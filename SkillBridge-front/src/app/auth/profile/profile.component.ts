import { CommonModule } from '@angular/common';
import { Component, OnInit } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Title } from '@angular/platform-browser';
import { Router, RouterModule } from '@angular/router';
import { JobService } from '../../services/job.service';
import { JobOffer } from '../../models/job-offer.model';
import { Country, State, City } from 'country-state-city';
import { LoaderModalComponent } from '../../shared/loader-modal/loader-modal.component';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';


@Component({
  selector: 'app-profile',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, RouterModule, LoaderModalComponent],
  templateUrl: './profile.component.html',
  styleUrls: ['./profile.component.scss']
})

export class ProfileComponent implements OnInit {
  profileForm!: FormGroup;
  selectedFile: File | null = null;
  errorMessage = "";
  isLoading = false;
  showLoader = false;
  successMessage = "";
  countryCodes: any[] = []
  countries = Country.getAllCountries();
  states: any[] = []
  cities: any[] = [];

  constructor(
    private fb: FormBuilder, 
    private http: HttpClient, 
    private router: Router,
    private jobService: JobService,
    private titleService: Title
  ) {
    this.titleService.setTitle('SkillBridge - Home');
  }

  ngOnInit(): void {
    this.http.get<any[]>('/data/country-code.json').subscribe(data => {
      this.countryCodes = data;
    });
    this.profileForm = this.fb.group({
      first_name: ['', Validators.required],
      last_name: ['', Validators.required],
      number_id: ['', Validators.required],
      phone_code: ['', Validators.required],
      phone_number: ['', Validators.required],
      country: ['', Validators.required],
      city: ['', Validators.required],
      professional_title: ['', Validators.required],
      summary: ['', Validators.required],
      education: ['', Validators.required],
      skills: ['', Validators.required],
      experience: ['', Validators.required],
      linkedin_url: ['', [Validators.required, Validators.pattern(/^https?:\/\/(www\.)?linkedin\.com\/in\/[^\s]+$/)]],
      portfolio_url: [''],
      resume: [null],
    });
  }

  getFlagEmoji(countryCode: string): string {
    if (!countryCode || countryCode.length !== 2) return '';
    const codePoints = [...countryCode.toUpperCase()]
      .map(char => 127397 + char.charCodeAt(0));
    return String.fromCodePoint(...codePoints);
  }

  onCountryChange(countryCode: string): void {
    const selected = this.countries.find(c => c.isoCode === countryCode);
    if (selected) {
      this.profileForm.patchValue({
        phone_code: `+${selected?.phonecode}`
      });
      this.cities = City.getCitiesOfCountry(countryCode) ?? [];
    }
  }

  onFileSelected(event:any) {
    this.selectedFile = event.target.files[0];
    if (!this.selectedFile) return;
    const formData = new FormData();
    formData.append('resume', this.selectedFile);
    this.isLoading = true;
    this.http.post<any>('http://localhost:8000/api/users/resume-analyzer/', formData).subscribe({
      next: (data) => {
        const phoneCode = data.phone_code.replace('+', '');
        const matchedCountry = this.countries.find(c => c.phonecode === phoneCode);
        const country_code = matchedCountry?.isoCode

        let linkedin = data.linkedin_url?.trim() || '';
        if (linkedin && !linkedin.startsWith('http')) {
          // Make a sure that match with https://www.
          if (!linkedin.startsWith('www.')) {
            linkedin = 'https://www.' + linkedin;
          } else {
            linkedin = 'https://' + linkedin;
          }
        }

        this.profileForm.patchValue({
          first_name: data.first_name,
          last_name: data.last_name,
          phone_code: data.phone_code,
          phone_number: data.phone_number,
          country: country_code || '',
          city: data.city,
          professional_title: data.professional_title,
          summary: data.summary,
          education: data.education,
          skills: data.skills,
          experience: data.experience,
          linkedin_url: linkedin,
          portfolio_url: data.portfolio_url
        });
        if (country_code) this.onCountryChange(country_code);
        this.successMessage = "Hoja de vida analizada correctamente";
        // console.log("📦 Datos recibidos:", data)
        Object.keys(this.profileForm.controls).forEach(field => {
          const control = this.profileForm.get(field);
          control?.markAsTouched();
          control?.updateValueAndValidity();
        });
        this.isLoading = false;
      },
      error: () => {
        this.errorMessage = "Error al analizar hoja de vida"
      }
    });
  }

  onSubmit() {
    if (this.profileForm.invalid) return;
    const formData = new FormData();
    Object.entries(this.profileForm.value).forEach(([key, value]) => {
      if (value instanceof File && value instanceof File) {
        formData.append(key, value);
      }else if (value !== null && value !== undefined) {
        formData.append(key, String(value));
      }
    });
    if (this.selectedFile) {
      formData.append('resume', this.selectedFile);
    }
    const token = localStorage.getItem('access_token');
    const headers = {Authorization: `Bearer ${token}`};
    this.isLoading = true;
    this.http.post('http://localhost:8000/api/users/profile/', formData, { headers }).subscribe({
      next: () => {
        setTimeout(() => {
          this.isLoading = false;
          console.log("✅ Perfil guardado correctamente");
          this.showLoader = true;
        }, 1500);
        this.jobService.getScrapedOffers().subscribe({
          next: (res: JobOffer[]) => {
            this.jobService.setOffers(res);
            this.showLoader = false;
            this.router.navigate(['/results']);
          },
          error: (err) => {
            this.showLoader = false;
            console.error("❌ Error al obtener vacantes:", err);
          }
        });
      },
      error: (err) => {
        this.isLoading = false;
        this.errorMessage = 'Error al completar perfil';
        console.error("❌ Error al guardar el perfil:", err);
      }
    });
  }
}
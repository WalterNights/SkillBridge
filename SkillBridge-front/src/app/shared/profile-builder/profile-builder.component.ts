import { Router } from '@angular/router';
import { Injectable } from "@angular/core";
import { Country, City } from 'country-state-city';
import { JobService } from '../../services/job.service';
import { JobOffer } from '../../models/job-offer.model';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { FormBuilder, FormGroup, Validators } from '@angular/forms';

@Injectable({ providedIn: 'root'})
export class ProfileBuilderComponent {
  profileForm: any;
  countryCodes: any[] = [];
  cities: any[] = [];

  constructor(
    private fb: FormBuilder,
    private http: HttpClient,
    private jobService: JobService,
    private router: Router
  ) {}

  buildProfileForm(): FormGroup {
    return this.fb.group({
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

  getCitiesByCountryCode(countryCode: string): any[] {
    return City.getCitiesOfCountry(countryCode) ?? [];
  }

  extractPhoneCode(countries: any[], countryCode: string) {
    const selected = countries.find(c => c.isoCode === countryCode);
    return selected ? `+${selected.phonecode}` : '';
  }

  analyzeResume(
    file: File,
    countries = Country.getAllCountries(),
    calback: (data: any, countryCode: string) => void,
    onError?: () => void
  ) {
    const formData = new FormData();
    formData.append('resume', file);
    this.http.post<any>('http://localhost:8000/api/users/resume-analyzer/', formData).subscribe({
      next: (data) => {
        const phoneCode = data.phone_code.replace('+', '');
        const matchedCountry = countries.find(c => c.phonecode === phoneCode);
        const country_code = matchedCountry?.isoCode || '';
        let linkedin = data.linkedin_url?.trim() || '';
        if (linkedin && !linkedin.startsWith('http')) {
          // Make a sure that match with https://www.
          if (!linkedin.startsWith('www.')) {
            linkedin = 'https://www.' + linkedin;
          } else {
            linkedin = 'https://' + linkedin;
          }
        }
        const parsedData = {
          ...data,
          country: country_code,
          linkedin_url: linkedin
        };
        calback(parsedData, country_code)
      },
      error: () => {
        onError?.();
      }
    });
  }

  submitProfileData(
    profileForm: any,
    selectedFile: File | null = null,
    onStart?: () => void,
    onSuccess?: () => void,
    onError?: (err: any) => void
  ) {
    if (profileForm.invalid) return;
    const formData = new FormData();
    Object.entries(profileForm.value).forEach(([key, value]) => {
      if (value instanceof File && value instanceof File) {
        formData.append(key, value);
      }else if (value !== null && value !== undefined) {
        formData.append(key, String(value));
      }
    });
    if (selectedFile) formData.append('resume', selectedFile);
    const token = localStorage.getItem('access_token');
    const headers = new HttpHeaders({Authorization: `Bearer ${token}`});
    onStart?.();
    this.http.post('http://localhost:8000/api/users/profile/', formData, { headers }).subscribe({
      next: () => {
        onSuccess?.();
        this.jobService.getScrapedOffers().subscribe({
          next: (res: JobOffer[]) => {
            this.jobService.setOffers(res);
            this.router.navigate(['/results']);
          },
          error: (err) => {
            console.error("❌ Error al obtener vacantes:", err);
          }
        });
      },
      error: (err) => {
        console.error("❌ Error al guardar el perfil:", err);
        onError?.(err);
      }
    });
  }
}

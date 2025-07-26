import { Router } from '@angular/router';
import { Injectable } from "@angular/core";
import { Country, City } from 'country-state-city';
import { JobService } from '../../services/job.service';
import { JobOffer } from '../../models/job-offer.model';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { FormArray, FormBuilder, FormGroup, Validators } from '@angular/forms';


@Injectable({ providedIn: 'root' })
export class ProfileBuilderComponent {
  profileForm: any;
  countryCodes: any[] = [];
  cities: any[] = [];
  countries = Country.getAllCountries();

  constructor(
    private fb: FormBuilder,
    private http: HttpClient,
    private jobService: JobService,
    private router: Router
  ) { }

  buildProfileForm(overrides: Partial<{
    education: FormArray,
    experience: FormArray
  }> = {}): FormGroup {
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
      education: overrides.education ?? this.fb.control('', Validators.required),
      experience: overrides.experience ?? this.fb.control('', Validators.required),
      skills: ['', Validators.required],
      linkedin_url: ['', [Validators.required, Validators.pattern(/^(https?:\/\/)?(www\.)?linkedin\.com\/in\/[a-zA-Z0-9_-]+\/?$/)]],
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
    country_find = this.countries,
    calback: (data: any, countryCode: string) => void,
    onError?: () => void
  ) {
    const formData = new FormData();
    formData.append('resume', file);
    this.http.post<any>('http://localhost:8000/api/users/resume-analyzer/', formData).subscribe({
      next: (data) => {
        const phoneCode = data.phone_code.replace('+', '');
        const matchedCountry = country_find.find(c => c.phonecode === phoneCode);
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
    onError?: (err: any) => void,
    shouldRedirect: boolean = true
  ) {
    if (profileForm.invalid) return;
    const formData = new FormData();
    // If data come from manual-profile
    const rawData = profileForm.value
    // Check if linkedin url have not http://www.
    if (rawData.linkedin_url && !rawData.linkedin_url.startsWith('http')) {
      rawData.linkedin_url = `https://www.${rawData.linkedin_url}`;
    }
    if (rawData.country) {
      const findCountry = this.countries.find(c => c.isoCode === rawData.country);
      rawData.country = findCountry != undefined ? findCountry.name : rawData.country;
    }
    if (Array.isArray(rawData.education) && Array.isArray(rawData.experience)) {
      if (rawData.education.length > 0) {
        const education = rawData.education.map((edu: any) => {
          const findCountry = this.countries.find(c => c.isoCode === edu.location_country);
          edu.location_country = findCountry != undefined ? findCountry.name : edu.location_country;
          return `${edu.title} en ${edu.institution} - (${edu.location_city}, ${edu.location_country}) - ${edu.start_date} a ${edu.end_date}`;
        }).join('\n\n');
        formData.append('education', education);
      }
      if (rawData.experience.length > 0) {
        const experiences = rawData.experience.map((exp: any) => {
          const findCountry = this.countries.find(c => c.isoCode === exp.location_country);
          exp.location_country = findCountry != undefined ? findCountry.name : exp.location_country;;
          return `${exp.position} en ${exp.company} - (${exp.location_city}, ${exp.location_country}) - ${exp.start_date} a ${exp.end_date}:\n ${exp.description}`;
        }).join('\n\n');
        formData.append('experience', experiences);
      }
      localStorage.setItem('manual_profile_draft', JSON.stringify(rawData));
    } else {
      if (typeof rawData.education === 'string' && rawData.education.trim() !== '') {
        formData.append('education', rawData.education);
      }
      if (typeof rawData.experience === 'string' && rawData.experience.trim() !== '') {
        formData.append('experience', rawData.experience);
      }
    }
    // If data have array for education and experience
    Object.entries(rawData).forEach(([key, value]) => {
      if (['education', 'experience'].includes(key)) return;
      if (value instanceof File) {
        formData.append(key, value);
      } else if (value !== null && value !== undefined) {
        formData.append(key, String(value));
      }
    });
    selectedFile = rawData.resume;
    if (selectedFile instanceof File) formData.append('resume', selectedFile);
    const token = localStorage.getItem('access_token');
    const headers = new HttpHeaders({ Authorization: `Bearer ${token}` });
    onStart?.();
    this.http.post('http://localhost:8000/api/users/profile/', formData, { headers }).subscribe({
      next: (res: any) => {
        onSuccess?.();
        if (res) {
          sessionStorage.setItem('is_profile_complete', 'true');
          sessionStorage.setItem('user_name', res.first_name);
        }
        this.jobService.getScrapedOffers().subscribe({
          next: (res: JobOffer[]) => {
            this.jobService.setOffers(res);
            if (shouldRedirect) {
              this.router.navigate(['/results']);
            } else {
              this.router.navigate(['/ats-cv']);
            }
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
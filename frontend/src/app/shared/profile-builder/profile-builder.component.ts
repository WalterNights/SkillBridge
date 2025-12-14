import { Router } from '@angular/router';
import { Injectable } from "@angular/core";
import { Country, City } from 'country-state-city';
import { JobService } from '../../services/job.service';
import { JobOffer } from '../../models/job-offer.model';
import { HttpClient, HttpHeaders, HttpErrorResponse } from '@angular/common/http';
import { FormArray, FormBuilder, FormGroup, Validators } from '@angular/forms';
import { CountryData, CityData } from '../../models/country.model';
import { ResumeAnalysisData, ProfileFormData, EducationEntry, ExperienceEntry } from '../../models/profile.model';
import { environment } from '../../../environment/environment';
import { STORAGE_KEYS } from '../../constants/app-stats';

/**
 * Service for building and managing user profile forms
 */
@Injectable({ providedIn: 'root' })
export class ProfileBuilderComponent {
  profileForm: FormGroup | null = null;
  countryCodes: CountryData[] = [];
  cities: CityData[] = [];
  countries = Country.getAllCountries();

  constructor(
    private fb: FormBuilder,
    private http: HttpClient,
    private jobService: JobService,
    private router: Router
  ) { }

  /**
   * Builds a profile form with optional overrides
   * @param overrides - Optional form array overrides for education and experience
   * @returns Configured FormGroup
   */
  buildProfileForm(overrides: Partial<{
    education: FormArray,
    experience: FormArray
  }> = {}): FormGroup {
    return this.fb.group({
      first_name: ['', Validators.required],
      last_name: ['', Validators.required],
      email: ['', [Validators.required, Validators.email]],
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

  /**
   * Gets cities for a specific country code
   * @param countryCode - ISO country code
   * @returns Array of cities
   */
  getCitiesByCountryCode(countryCode: string): CityData[] {
    return City.getCitiesOfCountry(countryCode) ?? [];
  }

  /**
   * Extracts phone code from country data
   * @param countries - Array of country data
   * @param countryCode - ISO country code
   * @returns Phone code with '+' prefix
   */
  extractPhoneCode(countries: CountryData[], countryCode: string): string {
    const selected = countries.find(c => c.isoCode === countryCode);
    return selected ? `+${selected.phonecode}` : '';
  }

  /**
   * Analyzes a resume file and extracts structured data
   * @param file - Resume file (PDF, DOCX, etc.)
   * @param country_find - Array of countries to match phone codes
   * @param callback - Success callback with parsed data
   * @param onError - Optional error callback
   */
  analyzeResume(
    file: File,
    country_find: CountryData[] = this.countries,
    callback: (data: ResumeAnalysisData, countryCode: string) => void,
    onError?: () => void
  ): void {
    const formData = new FormData();
    formData.append('resume', file);
    this.http.post<ResumeAnalysisData>(`${environment.apiUrl}/users/resume-analyzer/`, formData).subscribe({
      next: (data) => {
        const phoneCode = data.phone_code.replace('+', '');
        const matchedCountry = country_find.find(c => c.phonecode === phoneCode);
        const country_code = matchedCountry?.isoCode || '';
        let linkedin = data.linkedin_url?.trim() || '';

        // Ensure LinkedIn URL has proper protocol prefix
        if (linkedin && !linkedin.startsWith('http')) {
          if (!linkedin.startsWith('www.')) {
            linkedin = 'https://www.' + linkedin;
          } else {
            linkedin = 'https://' + linkedin;
          }
        }

        const parsedData: ResumeAnalysisData = {
          ...data,
          country: country_code,
          linkedin_url: linkedin
        };
        callback(parsedData, country_code);
      },
      error: () => {
        onError?.();
      }
    });
  }

  /**
   * Submits profile data to the backend
   * @param profileForm - Form group containing profile data
   * @param selectedFile - Optional resume file
   * @param onStart - Optional callback when submission starts
   * @param onSuccess - Optional callback on successful submission
   * @param onError - Optional error callback
   * @param shouldRedirect - Whether to redirect after success (default: true)
   */
  submitProfileData(
    profileForm: FormGroup,
    selectedFile: File | null = null,
    onStart?: () => void,
    onSuccess?: () => void,
    onError?: (err: HttpErrorResponse) => void,
    shouldRedirect: boolean = true
  ): void {
    if (profileForm.invalid) return;

    const formData = new FormData();
    const rawData = profileForm.value as ProfileFormData;

    // Ensure LinkedIn URL has proper protocol prefix
    if (rawData.linkedin_url && !rawData.linkedin_url.startsWith('http')) {
      rawData.linkedin_url = `https://www.${rawData.linkedin_url}`;
    }

    // Convert country code to country name
    if (rawData.country) {
      const findCountry = this.countries.find(c => c.isoCode === rawData.country);
      rawData.country = findCountry?.name ?? rawData.country;
    }

    // Only add user email from session if not provided in the form
    if (!rawData.email || rawData.email.trim() === '') {
      const userEmail = sessionStorage.getItem('user_email');
      if (userEmail) {
        rawData.email = userEmail;
      }
    }

    // Process education and experience arrays
    if (Array.isArray(rawData.education) && Array.isArray(rawData.experience)) {
      // Convert education array to formatted strings for backend
      if (rawData.education.length > 0) {
        const educationText = rawData.education.map((edu: EducationEntry) => {
          const findCountry = this.countries.find(c => c.isoCode === edu.location_country);
          const countryName = findCountry?.name ?? edu.location_country;
          // Update the location_country in the original object for localStorage
          edu.location_country = countryName;
          return `${edu.title} en ${edu.institution} - (${edu.location_city}, ${countryName}) - ${edu.start_date} a ${edu.end_date}`;
        }).join('\n\n');
        formData.append('education', educationText);
      }

      // Convert experience array to formatted strings for backend
      if (rawData.experience.length > 0) {
        const experiencesText = rawData.experience.map((exp: ExperienceEntry) => {
          const findCountry = this.countries.find(c => c.isoCode === exp.location_country);
          const countryName = findCountry?.name ?? exp.location_country;
          // Update the location_country in the original object for localStorage
          exp.location_country = countryName;
          return `${exp.position} en ${exp.company} - (${exp.location_city}, ${countryName}) - ${exp.start_date} a ${exp.end_date}:\n ${exp.description}`;
        }).join('\n\n');
        formData.append('experience', experiencesText);
      }

      // Save to localStorage with arrays intact and email included
      localStorage.setItem(STORAGE_KEYS.MANUAL_PROFILE_DRAFT, JSON.stringify(rawData));
    } else {
      // Handle string format for education and experience
      if (typeof rawData.education === 'string' && rawData.education.trim() !== '') {
        formData.append('education', rawData.education);
      }
      if (typeof rawData.experience === 'string' && rawData.experience.trim() !== '') {
        formData.append('experience', rawData.experience);
      }

      // Save to localStorage even for string format with email included
      localStorage.setItem(STORAGE_KEYS.MANUAL_PROFILE_DRAFT, JSON.stringify(rawData));
    }

    // Append all other form fields
    Object.entries(rawData).forEach(([key, value]) => {
      if (['education', 'experience'].includes(key)) return;
      if (value instanceof File) {
        formData.append(key, value);
      } else if (value !== null && value !== undefined) {
        formData.append(key, String(value));
      }
    });

    // Append resume file if provided
    selectedFile = rawData.resume ?? null;
    if (selectedFile instanceof File) {
      formData.append('resume', selectedFile);
    }

    const token = localStorage.getItem(STORAGE_KEYS.ACCESS_TOKEN);
    const headers = new HttpHeaders({ Authorization: `Bearer ${token}` });

    onStart?.();

    this.http.post<{ first_name: string }>(`${environment.apiUrl}/users/profiles/`, formData, { headers }).subscribe({
      next: (res) => {
        onSuccess?.();
        if (res) {
          sessionStorage.setItem(STORAGE_KEYS.PROFILE_COMPLETE, 'true');
          sessionStorage.setItem(STORAGE_KEYS.USER_NAME, res.first_name);
        }

        // Intentar obtener ofertas de trabajo, pero navegar independientemente del resultado
        this.jobService.getScrapedOffers().subscribe({
          next: (jobRes: JobOffer[]) => {
            this.jobService.setOffers(jobRes);
          },
          error: (err: HttpErrorResponse) => {
            console.warn('Error fetching job offers, continuing anyway:', err);
            // Limpiar ofertas si hay error
            this.jobService.setOffers([]);
          }
        });

        // Navegar después de guardar el perfil solo si shouldRedirect es true
        // Si shouldRedirect es false, el componente que llama manejará la navegación
        if (shouldRedirect) {
          this.router.navigate(['/results']);
        }
      },
      error: (err: HttpErrorResponse) => {
        console.error('Error saving profile:', err);
        onError?.(err);
      }
    });
  }
}

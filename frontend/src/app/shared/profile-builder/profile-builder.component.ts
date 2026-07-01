import { Router } from '@angular/router';
import { Injectable } from '@angular/core';
import { Country, City } from 'country-state-city';
import { JobService } from '../../services/job.service';
import { JobOffer } from '../../models/job-offer.model';
import { HttpClient, HttpHeaders, HttpErrorResponse } from '@angular/common/http';
import { FormArray, FormBuilder, FormGroup, Validators } from '@angular/forms';
import { CountryData, CityData } from '../../models/country.model';
import {
  ResumeAnalysisData,
  ProfileFormData,
  EducationEntry,
  ExperienceEntry,
} from '../../models/profile.model';
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
    private router: Router,
  ) {}

  /**
   * Builds a profile form with optional overrides
   * @param overrides - Optional form array overrides for education and experience
   * @returns Configured FormGroup
   */
  buildProfileForm(
    overrides: Partial<{
      education: FormArray;
      experience: FormArray;
    }> = {},
  ): FormGroup {
    return this.fb.group({
      first_name: ['', Validators.required],
      last_name: ['', Validators.required],
      email: ['', [Validators.required, Validators.email]],
      number_id: ['', Validators.required],
      phone_code: [''],
      phone_number: ['', Validators.required],
      country: [''],
      city: ['', Validators.required],
      professional_title: ['', Validators.required],
      summary: ['', Validators.required],
      education: overrides.education ?? this.fb.control('', Validators.required),
      experience: overrides.experience ?? this.fb.control('', Validators.required),
      skills: ['', Validators.required],
      linkedin_url: [
        '',
        Validators.pattern(/^(https?:\/\/)?(www\.)?linkedin\.com\/in\/[a-zA-Z0-9%_-]+\/?$/),
      ],
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
    const selected = countries.find((c) => c.isoCode === countryCode);
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
    onError?: () => void,
  ): void {
    const formData = new FormData();
    formData.append('resume', file);
    this.http
      .post<ResumeAnalysisData>(`${environment.apiUrl}/users/resume-analyzer/`, formData)
      .subscribe({
        next: (data) => {
          const phoneCode = data.phone_code.replace('+', '');
          const matchedCountry = country_find.find((c) => c.phonecode === phoneCode);
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
            linkedin_url: linkedin,
          };

          // Guardar los datos estructurados en localStorage para el CV ATS
          // Esto incluye los arrays de education y experience
          localStorage.setItem(STORAGE_KEYS.MANUAL_PROFILE_DRAFT, JSON.stringify(parsedData));

          callback(parsedData, country_code);
        },
        error: () => {
          onError?.();
        },
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
    shouldRedirect: boolean = true,
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
      const findCountry = this.countries.find((c) => c.isoCode === rawData.country);
      rawData.country = findCountry?.name ?? rawData.country;
    }

    // Only add user email from session if not provided in the form
    if (!rawData.email || rawData.email.trim() === '') {
      const userEmail = sessionStorage.getItem('user_email');
      if (userEmail) {
        rawData.email = userEmail;
      }
    }

    // Try to get existing localStorage data (may have arrays from resume analysis)
    const existingData = localStorage.getItem(STORAGE_KEYS.MANUAL_PROFILE_DRAFT);
    let existingParsed: any = null;
    if (existingData) {
      try {
        existingParsed = JSON.parse(existingData);
      } catch (e) {
        existingParsed = null;
      }
    }

    // Check if we have arrays in existing data (from resume analysis)
    const hasExistingEducationArray =
      Array.isArray(existingParsed?.education) && existingParsed.education.length > 0;
    const hasExistingExperienceArray =
      Array.isArray(existingParsed?.experience) && existingParsed.experience.length > 0;

    // Process education and experience — CADA campo se maneja de forma
    // independiente porque en /me un user puede migrar SOLO uno de los
    // dos (education a estructurado, experience seguir legacy o al revés).
    // La lógica vieja pedía "AMBOS arrays" y perdía el campo que sí venía
    // migrado cuando el otro era string.
    //
    // Nuevo formato de persistencia: JSON stringified — /cv ya sabe
    // parsear ambos (ver `parseEntriesField` en ats-cv.component.ts).
    const normalizeCountry = (isoOrName: string | undefined): string | undefined => {
      if (!isoOrName) return isoOrName;
      const found = this.countries.find((c) => c.isoCode === isoOrName);
      return found?.name ?? isoOrName;
    };

    // Education
    if (Array.isArray(rawData.education)) {
      if (rawData.education.length > 0) {
        const normalizedEdu = rawData.education.map((edu: EducationEntry) => ({
          ...edu,
          location_country: normalizeCountry(edu.location_country),
        }));
        formData.append('education', JSON.stringify(normalizedEdu));
      } else {
        // Array vacío — mandar string vacío para que backend lo limpie
        formData.append('education', '');
      }
    } else if (typeof rawData.education === 'string' && rawData.education.trim() !== '') {
      formData.append('education', rawData.education);
    }

    // Experience
    if (Array.isArray(rawData.experience)) {
      if (rawData.experience.length > 0) {
        const normalizedExp = rawData.experience.map((exp: ExperienceEntry) => ({
          ...exp,
          location_country: normalizeCountry(exp.location_country),
        }));
        formData.append('experience', JSON.stringify(normalizedExp));
      } else {
        formData.append('experience', '');
      }
    } else if (typeof rawData.experience === 'string' && rawData.experience.trim() !== '') {
      formData.append('experience', rawData.experience);
    }

    // localStorage draft: preservar arrays si vienen, sino usar strings
    const dataToSave: any = { ...rawData };
    if (hasExistingEducationArray && typeof rawData.education === 'string') {
      dataToSave.education = existingParsed.education;
    }
    if (hasExistingExperienceArray && typeof rawData.experience === 'string') {
      dataToSave.experience = existingParsed.experience;
    }
    localStorage.setItem(STORAGE_KEYS.MANUAL_PROFILE_DRAFT, JSON.stringify(dataToSave));

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

    this.http
      .post<{ first_name: string }>(`${environment.apiUrl}/users/profiles/`, formData, { headers })
      .subscribe({
        next: (res) => {
          onSuccess?.();
          if (res) {
            sessionStorage.setItem(STORAGE_KEYS.PROFILE_COMPLETE, 'true');
            sessionStorage.setItem(STORAGE_KEYS.USER_NAME, res.first_name);
          }

          // Intentar obtener ofertas de trabajo, pero navegar independientemente del resultado
          this.jobService.getScrapedOffers().subscribe({
            next: (jobRes) => {
              this.jobService.setOffers(jobRes.offers ?? []);
            },
            error: (err: HttpErrorResponse) => {
              console.warn('Error fetching job offers, continuing anyway:', err);
              // Limpiar ofertas si hay error
              this.jobService.setOffers([]);
            },
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
        },
      });
  }
}

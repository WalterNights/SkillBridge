import { Country } from 'country-state-city';
import { Router, RouterModule } from '@angular/router';
import { CommonModule, Location } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { Component, OnInit } from '@angular/core';
import { Title } from '@angular/platform-browser';
import { FormGroup, ReactiveFormsModule } from '@angular/forms';
import { LoaderModalComponent } from '../../shared/loader-modal/loader-modal.component';
import { ProfileBuilderComponent } from '../../shared/profile-builder/profile-builder.component';


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
  profileSaved = false;
  countryCodes: any[] = [];
  countries = Country.getAllCountries();
  cities: any[] = [];

  constructor(
    private http: HttpClient,
    private profileBuldier: ProfileBuilderComponent,
    private titleService: Title,
    private location: Location,
    private router: Router
  ) {
    this.titleService.setTitle('SkilTak - Home');
  }

  ngOnInit(): void {
    this.http.get<any[]>('assets/data/country-code.json').subscribe(data => {
      this.countryCodes = data;
    });
    this.profileForm = this.profileBuldier.buildProfileForm();
  }

  onCountryChange(countryCode: string): void {
    const phone = this.profileBuldier.extractPhoneCode(this.countries, countryCode);
    this.profileForm.patchValue({ phone_code: phone });
    this.cities = this.profileBuldier.getCitiesByCountryCode(countryCode);
  }

  onFileSelected(event: any) {
    this.selectedFile = event.target.files[0];
    if (!this.selectedFile) return;
    this.isLoading = true;
    this.profileBuldier.analyzeResume(
      this.selectedFile,
      this.countries,
      (data, country_code) => {
        // Convertir education array a texto para el formulario
        const educationText = this.formatEducationForForm(data.education);
        // Convertir experience array a texto para el formulario
        const experienceText = this.formatExperienceForForm(data.experience);

        this.profileForm.patchValue({
          first_name: data.first_name,
          last_name: data.last_name,
          phone_code: data.phone_code,
          phone_number: data.phone_number,
          country: country_code,
          city: data.city,
          professional_title: data.professional_title,
          summary: data.summary,
          education: educationText,
          skills: data.skills,
          experience: experienceText,
          linkedin_url: data.linkedin_url,
          portfolio_url: data.portfolio_url
        });
        if (country_code) this.onCountryChange(country_code);
        this.successMessage = "Hoja de vida analizada correctamente";
        Object.keys(this.profileForm.controls).forEach(field => {
          const control = this.profileForm.get(field);
          control?.markAsTouched();
          control?.updateValueAndValidity();
        });
        this.successMessage = "Hoja de vida analizada correctamente";
        this.isLoading = false;
      },
      () => {
        this.errorMessage = "Error al analizar hoja de vida"
        this.isLoading = false;
      }
    );
  }

  /**
   * Convierte el array de educación a texto legible para el formulario
   */
  formatEducationForForm(education: any): string {
    if (typeof education === 'string') return education;
    if (!Array.isArray(education)) return '';

    return education.map(edu => {
      const parts = [];
      if (edu.title) parts.push(edu.title);
      if (edu.institution) parts.push(`en ${edu.institution}`);
      if (edu.location_city || edu.location_country) {
        const location = [edu.location_city, edu.location_country].filter(Boolean).join(', ');
        parts.push(`(${location})`);
      }
      if (edu.start_date || edu.end_date) {
        const dates = [edu.start_date, edu.end_date].filter(Boolean).join(' - ');
        parts.push(`[${dates}]`);
      }
      return parts.join(' ');
    }).join('\n\n');
  }

  /**
   * Convierte el array de experiencia a texto legible para el formulario
   */
  formatExperienceForForm(experience: any): string {
    if (typeof experience === 'string') return experience;
    if (!Array.isArray(experience)) return '';

    return experience.map(exp => {
      const lines = [];
      // Primera línea: Empresa y ubicación
      const header = [exp.company];
      if (exp.location_city || exp.location_country) {
        const location = [exp.location_city, exp.location_country].filter(Boolean).join(', ');
        header.push(`(${location})`);
      }
      lines.push(header.join(' '));

      // Segunda línea: Puesto y fechas
      if (exp.position) {
        const positionLine = [exp.position];
        if (exp.start_date || exp.end_date) {
          const dates = [exp.start_date, exp.end_date].filter(Boolean).join(' - ');
          positionLine.push(`[${dates}]`);
        }
        lines.push(positionLine.join(' '));
      }

      // Descripción
      if (exp.description) {
        lines.push(exp.description);
      }

      return lines.join('\n');
    }).join('\n\n');
  }

  onSubmit() {
    this.profileBuldier.submitProfileData(
      this.profileForm,
      this.selectedFile,
      () => {
        this.isLoading = true;
        this.profileSaved = false;
      },
      () => {
        setTimeout(() => {
          this.isLoading = false;
          this.profileSaved = true;
          this.successMessage = '¡Perfil guardado exitosamente!';
          console.log("✅ Perfil guardado correctamente");
        }, 1500);
      },
      (err) => {
        this.isLoading = false;
        this.errorMessage = 'Error al completar perfil';
        this.profileSaved = false;
      },
      false // shouldRedirect: false para ir a /ats-cv
    );
  }

  /**
   * Navigate back to previous page
   */
  goBack(): void {
    this.location.back();
  }

  /**
   * Navigate to ATS CV page
   */
  goToAtsCv(): void {
    this.router.navigate(['/ats-cv']);
  }
}

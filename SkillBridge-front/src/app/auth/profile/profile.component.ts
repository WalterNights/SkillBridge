import { Country } from 'country-state-city';
import { RouterModule } from '@angular/router';
import { CommonModule } from '@angular/common';
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
  countryCodes: any[] = [];
  countries = Country.getAllCountries();
  cities: any[] = [];

  constructor(
    private http: HttpClient,
    private profileBuldier: ProfileBuilderComponent,
    private titleService: Title
  ) {
    this.titleService.setTitle('SkillBridge - Home');
  }

  ngOnInit(): void {
    this.http.get<any[]>('/data/country-code.json').subscribe(data => {
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
        this.profileForm.patchValue({
          first_name: data.first_name,
          last_name: data.last_name,
          phone_code: data.phone_code,
          phone_number: data.phone_number,
          country: country_code,
          city: data.city,
          professional_title: data.professional_title,
          summary: data.summary,
          education: data.education,
          skills: data.skills,
          experience: data.experience,
          linkedin_url: data.linkedin_url,
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
        this.successMessage = "Hoja de vida analizada correctamente";
        this.isLoading = false;
      },
      () => {
        this.errorMessage = "Error al analizar hoja de vida"
        this.isLoading = false;
      }
    );
  }

  onSubmit() {
    this.profileBuldier.submitProfileData(
      this.profileForm,
      this.selectedFile,
      () => { this.isLoading = true },
      () => {
        setTimeout(() => {
          this.isLoading = false;
          this.showLoader = true;
          console.log("✅ Perfil guardado correctamente");
        }, 1500);
      },
      (err) => {
        this.isLoading = false;
        this.errorMessage = 'Error al completar perfil';
      },
      true
    );
  }
}
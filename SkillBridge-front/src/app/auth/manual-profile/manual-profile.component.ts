import { Country } from 'country-state-city';
import { RouterModule } from '@angular/router';
import { CommonModule } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { Component, OnInit } from '@angular/core';
import { Title } from '@angular/platform-browser';
import { FormBuilder, FormArray, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { LoaderModalComponent } from '../../shared/loader-modal/loader-modal.component';
import { ProfileBuilderComponent } from '../../shared/profile-builder/profile-builder.component';


@Component({
  selector: 'app-manual-profile',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, RouterModule, LoaderModalComponent],
  templateUrl: './manual-profile.component.html',
  styleUrls: ['./manual-profile.component.scss']
})

export class ManualProfileComponent implements OnInit {
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
    private titleService: Title,
    private http: HttpClient,
    private fb: FormBuilder,
    private profileBuldier: ProfileBuilderComponent,
  ) {
    this.titleService.setTitle('SkillBridge - Registro Perfil Profesional');
  }

  ngOnInit(): void {
    this.http.get<any[]>('/data/country-code.json').subscribe(data => {
      this.countryCodes = data;
    });
    const educationArray = this.fb.array([this.createEducationGroup()]);
    const experienceArray = this.fb.array([this.createExperienceGroup()]);
    this.profileForm = this.profileBuldier.buildProfileForm({
      education: educationArray, 
      experience: experienceArray 
    });


    // DEBUGIN Autofill Form
    const savedForm = localStorage.getItem('manual_profile_draft');
    if (savedForm) {
      this.profileForm.patchValue(JSON.parse(savedForm));
    }
    this.profileForm.valueChanges.subscribe(val => {
      localStorage.setItem('manual_profile_draft', JSON.stringify(val));
    })


  }

  onCountryChange(countryCode: string): void {
    const phone = this.profileBuldier.extractPhoneCode(this.countries, countryCode);
    this.profileForm.patchValue({ phone_code: phone });
    this.cities = this.profileBuldier.getCitiesByCountryCode(countryCode);
  }

  get education(): FormArray {
    return this.profileForm.get('education') as FormArray;
  }

  get experience(): FormArray {
    return this.profileForm.get('experience') as FormArray;
  }

  createEducationGroup(): FormGroup {
    return this.fb.group({
      institution: ['', Validators.required],
      title: ['', Validators.required],
      location_country: [''],
      location_city: [''],
      start_date: ['', Validators.required],
      end_date: ['']
    });
  }

  createExperienceGroup(): FormGroup {
    return this.fb.group({
      company: ['', Validators.required],
      position: ['', Validators.required],
      location_country: [''],
      location_city: [''],
      start_date: ['', Validators.required],
      end_date: [''],
      description: ['', Validators.required]
    });
  }

  addEducation(): void {
    this.education.push(this.createEducationGroup());
  }

  addExperience(): void {
    this.experience.push(this.createExperienceGroup());
  }

  removeEducation(index: number): void {
    this.education.removeAt(index);
  }

  removeExperience(index: number): void {
    this.experience.removeAt(index);
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
          //localStorage.removeItem('manual_profile_draft');
        }, 1500);
      },
      (err) => {
        this.isLoading = false;
        this.errorMessage = 'Error al completar perfil';
      }
    );
  }
}
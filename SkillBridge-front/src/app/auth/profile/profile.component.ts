import { Router } from '@angular/router';
import { CommonModule } from '@angular/common';
import { Component, OnInit } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { FormBuilder, FormGroup, Validator, ReactiveFormsModule, Validators } from '@angular/forms';


@Component({
  selector: 'app-profile',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule],
  templateUrl: './profile.component.html',
  styleUrls: ['./profile.component.scss']
})
export class ProfileComponent implements OnInit {
  profileForm!: FormGroup;
  selectedFile: File | null = null;
  errorMessage = "";
  successMessage = "";
  countryCodes: any[] = []

  constructor(private fb: FormBuilder, private http: HttpClient, private router: Router) {}
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
      city: ['', Validators.required],
      education: ['', Validators.required],
      skills: ['', Validators.required],
      experience: ['', Validators.required],
      linkedin_url: ['', [Validators.required, Validators.pattern(/^https?:\/\/(www\.)?linkedin\.com\/in\/[^\s]+$/)]],
      portfolio_url: [''],
      resume: [null],
    });
  }

  onFileSelected(event:any) {
    this.selectedFile = event.target.files[0];
    if (!this.selectedFile) return;
    const formData = new FormData();
    formData.append('resume', this.selectedFile);
    this.http.post<any>('http://localhost:8000/api/users/resume/analyzer/', formData).subscribe({
      next: (data) => {
        this.profileForm.patchValue({
          first_name: data.first_name,
          last_name: data.last_name,
          phone_code: data.phone_code,
          phone_number: data.phone_number,
          city: data.city,
          education: data.education,
          skills: data.skills,
          experience: data.experience,
          linkedin_url: data.linkedin_url,
          portfolio_url: data.portfolio_url
        });
        this.successMessage = "Hoja de vida analizada correctamente";
        Object.keys(this.profileForm.controls).forEach(field => {
          const control = this.profileForm.get(field);
          control?.markAsTouched();
          control?.updateValueAndValidity();
        });
      },
      error: () => {
        this.errorMessage = "Error al analizar hoja de vida"
      }
    });
  }

  onSubmit() {
    console.log(this.profileForm.value)
    if (this.profileForm.invalid) {
      console.warn('⚠️ Formulario inválido', this.profileForm.errors);
      return
    };
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

    this.http.post('http://localhost:8000/api/users/profile/', formData, { headers }).subscribe({
      next: () => {
        console.log("✅ Perfil guardado correctamente");

        this.router.navigate(['/']);
      },
      error: (err) => {
        this.errorMessage = 'Error al completar perfil';
        console.error("❌ Error al guardar el perfil:", err);
      }
    });
  }
}

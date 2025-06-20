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

  constructor(private fb: FormBuilder, private http: HttpClient, private router: Router) {}
  ngOnInit(): void {
    this.profileForm = this.fb.group({
      first_name: ['', Validators.required],
      last_name: ['', Validators.required],
      number_id: ['', Validators.required],
      phone_code: ['', Validators.required],
      phone_number: ['', Validators.required],
      city: ['', Validators.required],
      education: [''],
      skills: [''],
      experience: [''],
      linkedin_url: [''],
      portfolio_url: [''],
      resume: [null],
    });
  }

  onFileSelected(event:any) {
    this.onFileSelected = event.target.files[0];
  }

  uploadCV() {
    if (!this.selectedFile) return;

    const formData = new FormData();
    formData.append('resume', this.selectedFile);

    this.http.post<any>('http://localhost:8000/api/users/resume/analyzer/', formData).subscribe({
      next: (data) => {
        this.profileForm.patchValue({
          first_name: data.first_name,
          last_name: data.last_name,
          edutacion: data.edutacion,
          skills: data.skills,
          linkedin_url: data.linkedin_url
        });
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
      if (value instanceof File) {
        formData.append(key, value);
      }else if (value !== null && value !== undefined) {
        formData.append(key, String(value));
      }
    });
    if (this.selectedFile) {
      formData.append('resume', this.selectedFile);
    }
    this.http.post('http://localhost:8000/api/users/profile/', formData).subscribe({
      next: () => {
        this,this.router.navigate(['/']);
      },
      error: () => {
        this.errorMessage = 'Error al completar perfil';
      }
    });
  }
}

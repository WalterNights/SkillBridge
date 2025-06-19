import { Router } from '@angular/router';
import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { environment } from '../../../environment/environment';
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

  onFileChange(event: any) {
    if (event.target.files.length > 0) {
      this.profileForm.patchValue({ resume: event.target.files[0]});
    }
  }
  onSubmit() {
    if (this.profileForm.invalid) return;
    const formData = new FormData();
    for (const key in this.profileForm.value) {
      formData.append(key, this.profileForm.value[key]);
    }
    this.http.post(`${environment.apiUrl}/api/users/profile/`, formData, {
      headers: {
        Authorization: `Bearer ${sessionStorage.getItem('access_token') || ''}`
      }
    }).subscribe({
      next: () => {
        this.successMessage = 'Perfil completado con éxito';
        sessionStorage.setItem('is_profile_complete', 'true');
        this.router.navigate(['/']);
      },
      error: err => {
        this.errorMessage = 'Error al guardar el perfil';
        console.error(err);
      }
    });
  }
}

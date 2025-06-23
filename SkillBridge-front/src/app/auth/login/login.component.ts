import { Router } from '@angular/router';
import { Component } from '@angular/core';
import { AuthService } from '../auth.service';
import { CommonModule } from '@angular/common';
import { environment } from '../../../environment/environment';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validator, Validators } from '@angular/forms';

@Component({
  selector: 'app-login',
  imports: [CommonModule, ReactiveFormsModule],
  standalone: true,
  templateUrl: './login.component.html',
  styleUrls: ['./login.component.scss']
})
export class LoginComponent {
  loginForm: FormGroup;
  errorMessage = '';
  constructor(private fb: FormBuilder, private authService: AuthService, private router: Router) {
    this.loginForm = this.fb.group({
      username: ['', Validators.required],
      password: ['', Validators.required]
    });
  }
  onSubmit() {
    if (this.loginForm.invalid) return;
    this.authService.login(this.loginForm.value).subscribe({
      next: () => {
        const isProfileComplete = sessionStorage.getItem('is_profile_complete') === 'true';
        this.router.navigate([isProfileComplete ? '/' : '/profile']);
      },
      error: () => {
        this.errorMessage = 'Credenciales inválidas. Intentalo nievamente.';
      }
    });
  }
}

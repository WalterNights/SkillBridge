import { Component } from '@angular/core';
import { AuthService } from '../auth.service';
import { CommonModule } from '@angular/common';
import { Title } from '@angular/platform-browser';
import { Router, RouterModule } from '@angular/router';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validator, Validators } from '@angular/forms';

@Component({
  selector: 'app-login',
  imports: [CommonModule, ReactiveFormsModule, RouterModule],
  standalone: true,
  templateUrl: './login.component.html',
  styleUrls: ['./login.component.scss']
})
export class LoginComponent {
  loginForm: FormGroup;
  isLoading = false;
  errorMessage = '';
  constructor(
    private fb: FormBuilder, 
    private authService: AuthService, 
    private router: Router,
    private titleService: Title
  ) {
    this.titleService.setTitle('SkillBridge - Login');
    this.loginForm = this.fb.group({
      username: ['', Validators.required],
      password: ['', Validators.required]
    });
  }
  onSubmit() {
    if (this.loginForm.invalid) return;
    this.isLoading = true;
    this.authService.login(this.loginForm.value).subscribe({
      next: () => {
        setTimeout(() => {
          this.isLoading = false;
          const isProfileComplete = sessionStorage.getItem('is_profile_complete') === 'true';
          this.router.navigate([isProfileComplete ? '/results' : '/profile']);
        }, 1200);
      },
      error: () => {
        this.isLoading = false;
        this.errorMessage = 'Credenciales inválidas. Intentalo nievamente.';
      }
    });
  }
}

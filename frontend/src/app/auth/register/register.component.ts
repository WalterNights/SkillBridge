import { Component } from '@angular/core';
import { AuthService } from '../auth.service';
import { CommonModule } from '@angular/common';
import { Title } from '@angular/platform-browser';
import { Router, RouterModule } from '@angular/router';
import { ReactiveFormsModule, FormBuilder, FormGroup, Validators, AbstractControl, ValidationErrors, ValidatorFn } from '@angular/forms';
import { HttpErrorResponse } from '@angular/common/http';

/**
 * Registration component for new user sign-up
 */
@Component({
  selector: 'app-register',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, RouterModule],
  templateUrl: './register.component.html',
  styleUrls: ['./register.component.scss']
})
export class RegisterComponent {
  registerForm!: FormGroup;
  isLoading = false;
  errorMessage = '';

  constructor(
    private fb: FormBuilder, 
    private authService: AuthService, 
    private router: Router,
    private titleService: Title
  ) {
    this.titleService.setTitle('SkilTak - Registro');
  }

  /**
   * Initializes component and sets up form
   */
  ngOnInit(): void {
    this.initializeForm();
  }

  /**
   * Initializes the registration form with validators
   */
  private initializeForm(): void {
    this.registerForm = this.fb.group({
      username: ['', Validators.required],
      email: ['', [Validators.required, Validators.email]],
      password: ['', [
        Validators.required,
        Validators.minLength(8), 
        Validators.pattern('^(?=.*[A-Za-z])(?=.*\\d)(?=.*[!@#$%^&*()_+{}:"<>?]).+$')
      ]],
      confirmPassword: ['', Validators.required]
    }, { validators: [this.passwordMatchValidator()] });
  }

  /**
   * Custom validator to check if password and confirmPassword match
   * @returns Validator function
   */
  passwordMatchValidator(): ValidatorFn {
    return (group: AbstractControl): ValidationErrors | null => {
      const password = group.get('password')?.value;
      const confirmPassword = group.get('confirmPassword')?.value;
      return password === confirmPassword ? null : { passwordsDoNotMatch: true };
    };
  }

  /**
   * Handles form submission and registration process
   */
  onSubmit(): void {
    if (this.registerForm.invalid) return;
    
    const { username, email, password } = this.registerForm.value;
    
    // Validate password doesn't match username or email
    if (password === username || password === email) {
      this.errorMessage = 'La contraseña no puede ser igual al nombre de usuario o correo';
      return;
    }
    
    this.isLoading = true;
    this.authService.register({ username, email, password }).subscribe({
      next: () => {
        setTimeout(() => {
          this.isLoading = false;
          this.router.navigate(['/auth/login']);
        }, 1500);
      },
      error: (err: HttpErrorResponse) => {
        this.isLoading = false;
        this.errorMessage = 'Error al registrar usuario. Intentelo nuevamente';
        console.error('Registration error:', err);
      }
    });
  }
}
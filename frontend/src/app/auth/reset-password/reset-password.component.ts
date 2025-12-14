import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ReactiveFormsModule, FormBuilder, FormGroup, Validators, AbstractControl, ValidationErrors } from '@angular/forms';
import { Router, ActivatedRoute, RouterModule } from '@angular/router';
import { AuthService } from '../auth.service';
import { HttpErrorResponse } from '@angular/common/http';

@Component({
  selector: 'app-reset-password',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, RouterModule],
  templateUrl: './reset-password.component.html',
  styleUrls: ['./reset-password.component.scss']
})
export class ResetPasswordComponent {
  resetPasswordForm!: FormGroup;
  isLoading = false;
  errorMessage = '';
  email = '';
  showPassword = false;
  showConfirmPassword = false;

  constructor(
    private fb: FormBuilder,
    private authService: AuthService,
    private router: Router,
    private route: ActivatedRoute
  ) {}

  ngOnInit(): void {
    // Obtener email de los query params
    this.route.queryParams.subscribe(params => {
      this.email = params['email'] || '';
    });

    this.resetPasswordForm = this.fb.group({
      email: [this.email, [Validators.required, Validators.email]],
      code: ['', [Validators.required, Validators.minLength(6), Validators.maxLength(6), Validators.pattern(/^\d{6}$/)]],
      newPassword: ['', [
        Validators.required,
        Validators.minLength(8),
        Validators.pattern('^(?=.*[A-Za-z])(?=.*\\d)(?=.*[!@#$%^&*()_+{}:"<>?]).+$')
      ]],
      confirmPassword: ['', Validators.required]
    }, { validators: this.passwordMatchValidator });
  }

  passwordMatchValidator(control: AbstractControl): ValidationErrors | null {
    const newPassword = control.get('newPassword')?.value;
    const confirmPassword = control.get('confirmPassword')?.value;
    return newPassword === confirmPassword ? null : { passwordsDoNotMatch: true };
  }

  onSubmit(): void {
    if (this.resetPasswordForm.invalid) return;

    this.isLoading = true;
    this.errorMessage = '';

    const { email, code, newPassword } = this.resetPasswordForm.value;

    this.authService.verifyPasswordReset({ email, code, new_password: newPassword }).subscribe({
      next: () => {
        this.isLoading = false;

        // Redirigir al login después de 2 segundos
        setTimeout(() => {
          this.router.navigate(['/auth/login']);
        }, 2000);
      },
      error: (err: HttpErrorResponse) => {
        this.isLoading = false;

        if (err.error && typeof err.error === 'object') {
          if (err.error.code) {
            this.errorMessage = 'Código inválido o expirado';
          } else if (err.error.non_field_errors) {
            this.errorMessage = err.error.non_field_errors[0] || 'Error al verificar el código';
          } else {
            this.errorMessage = 'Error al restablecer la contraseña';
          }
        } else {
          this.errorMessage = 'Error al restablecer la contraseña. Intenta nuevamente';
        }
      }
    });
  }

  togglePasswordVisibility(): void {
    this.showPassword = !this.showPassword;
  }

  toggleConfirmPasswordVisibility(): void {
    this.showConfirmPassword = !this.showConfirmPassword;
  }

  resendCode(): void {
    if (!this.email) return;

    this.authService.requestPasswordReset(this.email).subscribe({
      next: () => {
        this.errorMessage = '';
        alert('Nuevo código enviado a tu correo');
      },
      error: () => {
        this.errorMessage = 'Error al reenviar el código';
      }
    });
  }
}

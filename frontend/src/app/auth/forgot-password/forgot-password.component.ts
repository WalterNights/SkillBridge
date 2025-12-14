import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ReactiveFormsModule, FormBuilder, FormGroup, Validators } from '@angular/forms';
import { Router, RouterModule } from '@angular/router';
import { AuthService } from '../auth.service';
import { HttpErrorResponse } from '@angular/common/http';

@Component({
  selector: 'app-forgot-password',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, RouterModule],
  templateUrl: './forgot-password.component.html',
  styleUrls: ['./forgot-password.component.scss']
})
export class ForgotPasswordComponent {
  forgotPasswordForm!: FormGroup;
  isLoading = false;
  errorMessage = '';
  successMessage = '';

  constructor(
    private fb: FormBuilder,
    private authService: AuthService,
    private router: Router
  ) {}

  ngOnInit(): void {
    this.forgotPasswordForm = this.fb.group({
      email: ['', [Validators.required, Validators.email]]
    });
  }

  onSubmit(): void {
    if (this.forgotPasswordForm.invalid) return;

    this.isLoading = true;
    this.errorMessage = '';
    this.successMessage = '';

    const { email } = this.forgotPasswordForm.value;

    this.authService.requestPasswordReset(email).subscribe({
      next: (response) => {
        this.isLoading = false;
        this.successMessage = 'Código de verificación enviado a tu correo';

        // Redirigir a la página de verificación después de 2 segundos
        setTimeout(() => {
          this.router.navigate(['/auth/reset-password'], {
            queryParams: { email }
          });
        }, 2000);
      },
      error: (err: HttpErrorResponse) => {
        this.isLoading = false;

        if (err.error && err.error.email) {
          this.errorMessage = 'No existe un usuario con este correo electrónico';
        } else {
          this.errorMessage = 'Error al enviar el código. Intenta nuevamente';
        }
      }
    });
  }
}

import { Component } from '@angular/core';
import { AuthService } from '../auth.service';
import { CommonModule } from '@angular/common';
import { Router, RouterModule } from '@angular/router';
import { ReactiveFormsModule, FormBuilder, FormGroup, Validators, AbstractControl, ValidationErrors, ValidatorFn } from '@angular/forms';


@Component({
  selector: 'app-register',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, RouterModule],
  templateUrl: './register.component.html',
  styleUrls: ['./register.component.scss']
})

export class RegisterComponent {
  registerForm: FormGroup
  isLoading = false;
  errorMessage: string = '';
  constructor(private fb: FormBuilder, private authService: AuthService, private router: Router) {
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

  passwordMatchValidator(): ValidatorFn {
    return (group: AbstractControl): ValidationErrors | null => {
      const password = group.get('password')?.value;
      const confirmPassword = group.get('confirmPassword')?.value;
      return password === confirmPassword ? null : { passwordsDoNotMatch: true }
    };
  }

  onSubmit() {
    if (this.registerForm.invalid) return;
    const { username, email, password} = this.registerForm.value;
    if (password === username || password === email) {
      this.errorMessage = 'La contraseña no puede ser igual al nombre de usuario o correo'
    }
    this.isLoading = true;
    this.authService.register({ username, email, password }).subscribe({
      next: () => {
        setTimeout(() => {
          this.isLoading = false;
          this.router.navigate(['/auth/login'])
        }, 1500);
      },
      error: (err) => {
        this.isLoading = false;
        this.errorMessage = 'Error al registrar usuario. Intentelo nuevamente';
        console.error(err)
      }
    });
  }
}
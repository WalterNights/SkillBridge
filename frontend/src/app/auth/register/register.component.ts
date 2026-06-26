import { Component, OnInit, inject, signal } from '@angular/core';
import { AuthService, CompanyRegisterData } from '../auth.service';
import { CommonModule } from '@angular/common';
import { Title } from '@angular/platform-browser';
import { ActivatedRoute, Router, RouterModule } from '@angular/router';
import {
  ReactiveFormsModule,
  FormBuilder,
  FormGroup,
  Validators,
  AbstractControl,
  ValidationErrors,
  ValidatorFn,
} from '@angular/forms';
import { HttpErrorResponse } from '@angular/common/http';
import { environment } from '../../../environment/environment';

/** Step que está mostrando la vista. `select` es la pantalla inicial
 *  con dos cards; los otros dos son los forms específicos. Persistir
 *  el step en signal permite "volver" sin perder el form ya iniciado. */
type RegisterStep = 'select' | 'professional' | 'company';

/** Catálogo de "tamaños de empresa" — debe matchear el backend
 *  `CompanyProfile.COMPANY_SIZE_CHOICES`. */
const COMPANY_SIZE_OPTIONS = [
  { value: '1-10', label: '1-10 empleados' },
  { value: '11-50', label: '11-50 empleados' },
  { value: '51-200', label: '51-200 empleados' },
  { value: '201-500', label: '201-500 empleados' },
  { value: '501-1000', label: '501-1000 empleados' },
  { value: '1000+', label: 'Más de 1000 empleados' },
];

/**
 * Registro con selector inicial: profesional o empresa.
 *
 * Flow:
 *   1. Step `select` — dos cards visuales.
 *   2. Click → step `professional` (form existente) o `company` (form nuevo).
 *   3. Submit → POST al endpoint correspondiente → redirect a /auth/login.
 *
 * Query param `?type=professional|company` salta directo al form
 * apropiado — útil para deep-links desde el landing ("Soy empresa")
 * sin pasar por la pantalla de selección.
 */
@Component({
  selector: 'app-register',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, RouterModule],
  templateUrl: './register.component.html',
  styleUrls: ['./register.component.scss'],
})
export class RegisterComponent implements OnInit {
  private fb = inject(FormBuilder);
  private authService = inject(AuthService);
  private router = inject(Router);
  private route = inject(ActivatedRoute);
  private titleService = inject(Title);

  /** Step actual. Signal porque el HTML toma decisiones de render
   *  según este valor — más limpio que una propiedad pública mutable. */
  step = signal<RegisterStep>('select');

  // ─── Forms ────────────────────────────────────────────────────────
  registerForm!: FormGroup; // Profesional (mantenido idéntico al original)
  companyForm!: FormGroup; // Nuevo — empresa

  // ─── Estado UI ────────────────────────────────────────────────────
  isLoading = false;
  errorMessage = '';
  showPassword = false;
  showConfirmPassword = false;
  showCompanyPassword = false;

  readonly companySizeOptions = COMPANY_SIZE_OPTIONS;

  /** Mismo endpoint del backend que en login — arranca el flow OAuth
   * con LinkedIn. Solo aplica al form profesional. */
  readonly linkedInLoginUrl = `${environment.apiUrl}/auth/linkedin/start/`;

  constructor() {
    this.titleService.setTitle('SkilTak - Registro');
  }

  ngOnInit(): void {
    this.initializeForm();
    this.initializeCompanyForm();

    // Permitir deep-link directo a un form via ?type=
    const typeParam = this.route.snapshot.queryParamMap.get('type');
    if (typeParam === 'professional' || typeParam === 'company') {
      this.step.set(typeParam);
    }
  }

  // ─── Step navigation ──────────────────────────────────────────────

  goToStep(next: RegisterStep): void {
    this.errorMessage = '';
    this.step.set(next);
  }

  backToSelect(): void {
    this.goToStep('select');
  }

  // ─── Profesional (legacy form, intacto) ───────────────────────────

  private initializeForm(): void {
    this.registerForm = this.fb.group(
      {
        username: ['', Validators.required],
        email: ['', [Validators.required, Validators.email]],
        password: [
          '',
          [
            Validators.required,
            Validators.minLength(8),
            Validators.pattern('^(?=.*[A-Za-z])(?=.*\\d)(?=.*[!@#$%^&*()_+{}:"<>?]).+$'),
          ],
        ],
        confirmPassword: ['', Validators.required],
      },
      { validators: [this.passwordMatchValidator('password', 'confirmPassword')] },
    );
  }

  onSubmit(): void {
    if (this.registerForm.invalid) return;

    const { username, email, password } = this.registerForm.value;
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
        console.error('Registration error:', err);
        if (err.error && typeof err.error === 'object') {
          if (Array.isArray(err.error.username) && err.error.username.length > 0) {
            this.errorMessage = 'El nombre de usuario ya está en uso';
          } else if (Array.isArray(err.error.email) && err.error.email.length > 0) {
            this.errorMessage = 'El correo electrónico ya está registrado';
          } else if (Array.isArray(err.error.password) && err.error.password.length > 0) {
            this.errorMessage = 'La contraseña no cumple con los requisitos';
          } else {
            this.errorMessage =
              'Error al registrar usuario. Verifique los datos e intente nuevamente';
          }
        } else {
          this.errorMessage = 'Error al registrar usuario. Intentelo nuevamente';
        }
      },
    });
  }

  // ─── Empresa ──────────────────────────────────────────────────────

  private initializeCompanyForm(): void {
    this.companyForm = this.fb.group(
      {
        // Auth
        email: ['', [Validators.required, Validators.email]],
        password: ['', [Validators.required, Validators.minLength(8)]],
        confirmPassword: ['', Validators.required],

        // Empresa
        legal_name: ['', [Validators.required, Validators.maxLength(120)]],
        country: [''],
        city: [''],
        industry: [''],
        website: [''],
        size: [''],
        short_description: ['', Validators.maxLength(200)],

        // Responsable
        responsible_name: ['', [Validators.required, Validators.maxLength(100)]],
        responsible_role: ['', [Validators.required, Validators.maxLength(80)]],
        responsible_email: ['', [Validators.required, Validators.email]],
      },
      { validators: [this.passwordMatchValidator('password', 'confirmPassword')] },
    );
  }

  onSubmitCompany(): void {
    this.errorMessage = '';
    if (this.companyForm.invalid) {
      this.companyForm.markAllAsTouched();
      this.errorMessage = 'Revisá los campos marcados antes de continuar.';
      return;
    }

    const v = this.companyForm.value;
    const payload: CompanyRegisterData = {
      email: v.email,
      password: v.password,
      legal_name: v.legal_name,
      country: v.country || '',
      city: v.city || '',
      industry: v.industry || '',
      website: v.website || '',
      size: v.size || '',
      short_description: v.short_description || '',
      responsible_name: v.responsible_name,
      responsible_role: v.responsible_role,
      responsible_email: v.responsible_email,
    };

    this.isLoading = true;
    this.authService.registerCompany(payload).subscribe({
      next: () => {
        setTimeout(() => {
          this.isLoading = false;
          this.router.navigate(['/auth/login']);
        }, 1200);
      },
      error: (err: HttpErrorResponse) => {
        this.isLoading = false;
        console.error('Company registration error:', err);
        const body = err.error;
        if (body?.error) {
          this.errorMessage = body.error;
        } else if (body?.responsible_email?.length) {
          this.errorMessage =
            'Revisa el email del responsable — el formato no es válido.';
        } else if (body?.password?.length) {
          this.errorMessage = 'La contraseña debe tener al menos 8 caracteres.';
        } else if (body && typeof body === 'object') {
          // dict de field errors → fallback genérico mostrando el primer field
          const firstField = Object.keys(body)[0];
          const msg = Array.isArray(body[firstField]) ? body[firstField][0] : body[firstField];
          this.errorMessage = `${firstField}: ${msg}`;
        } else {
          this.errorMessage = 'Error al registrar la empresa. Intenta nuevamente.';
        }
      },
    });
  }

  // ─── Helpers ──────────────────────────────────────────────────────

  passwordMatchValidator(passwordKey: string, confirmKey: string): ValidatorFn {
    return (group: AbstractControl): ValidationErrors | null => {
      const password = group.get(passwordKey)?.value;
      const confirmPassword = group.get(confirmKey)?.value;
      return password === confirmPassword ? null : { passwordsDoNotMatch: true };
    };
  }

  togglePasswordVisibility(): void {
    this.showPassword = !this.showPassword;
  }
  toggleConfirmPasswordVisibility(): void {
    this.showConfirmPassword = !this.showConfirmPassword;
  }
  toggleCompanyPasswordVisibility(): void {
    this.showCompanyPassword = !this.showCompanyPassword;
  }
}

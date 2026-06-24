import { Component } from '@angular/core';
import { AuthService } from '../auth.service';
import { CommonModule } from '@angular/common';
import { Title } from '@angular/platform-browser';
import { Router, RouterModule } from '@angular/router';
import { StorageMethodComponent } from '../../shared/storage-method/storage-method';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { HttpErrorResponse } from '@angular/common/http';
import { STORAGE_KEYS } from '../../constants/app-stats';
import { environment } from '../../../environment/environment';

/**
 * Login component for user authentication
 */
@Component({
  selector: 'app-login',
  imports: [CommonModule, ReactiveFormsModule, RouterModule],
  standalone: true,
  templateUrl: './login.component.html',
  styleUrls: ['./login.component.scss'],
})
export class LoginComponent {
  loginForm!: FormGroup;
  isLoading = false;
  errorMessage = '';
  isStorage = false;
  storage: 'session' | 'local' = 'session';
  showPassword = false;

  /** URL del endpoint del backend que arranca el flow OAuth con LinkedIn.
   * Usamos un `<a href>` simple (no fetch) — el flow OAuth requiere
   * navegación top-level del browser para que LinkedIn pueda hacer
   * el redirect de vuelta. */
  readonly linkedInLoginUrl = `${environment.apiUrl}/auth/linkedin/start/`;

  constructor(
    private fb: FormBuilder,
    private authService: AuthService,
    private router: Router,
    private titleService: Title,
    private storageMethod: StorageMethodComponent,
  ) {
    this.titleService.setTitle('SkilTak - Login');
  }

  /**
   * Initializes component and sets up form
   */
  ngOnInit(): void {
    this.initializeForm();
    this.loadStoragePreference();
  }

  /**
   * Initializes the login form
   */
  private initializeForm(): void {
    this.loginForm = this.fb.group({
      username: ['', Validators.required],
      password: ['', Validators.required],
    });
  }

  /**
   * Loads storage preference from localStorage para reflejar
   * visualmente la última elección del user — solo si esa elección
   * todavía vive en localStorage (no la borramos al logout, queda
   * como sticky preference). No setea this.storage acá — lo decide
   * el submit basado en this.isStorage al momento de loguear.
   */
  private loadStoragePreference(): void {
    if (localStorage.getItem(STORAGE_KEYS.STORAGE_PREFERENCE) === 'true') {
      this.isStorage = true;
    }
  }

  /**
   * Toggle del switch. SOLO cambia el state local — la preferencia
   * se persiste recién al hacer login exitoso (AuthService.login con
   * `remember: this.isStorage`). Antes escribíamos a localStorage
   * inmediatamente, lo que filtraba la elección de un user al
   * siguiente en una compu compartida si el primero toggleaba pero
   * nunca terminaba de loguear.
   */
  toggleStorage(): void {
    this.isStorage = !this.isStorage;
  }

  /**
   * Handles form submission and login process.
   *
   * Redirect priority post-login:
   *   1. Intent explícito (REDIRECT_AFTER_LOGIN) — el AutoGuard lo
   *      setea cuando el usuario intentaba abrir una ruta privada y
   *      lo bouncearon al login. Respetar lo que quería ver.
   *   2. Si el perfil ya está completo → /dashboard (home del usuario).
   *   3. Si el perfil NO está completo → /profile, para que arme su
   *      perfil sin dar un click extra. Antes íbamos al landing y el
   *      usuario tenía que descubrir "Mi perfil" por su cuenta.
   */
  onSubmit(): void {
    if (this.loginForm.invalid) return;

    this.isLoading = true;
    // Pasamos `this.isStorage` como el flag `remember` — el AuthService
    // se encarga de persistir la preferencia + escribir tokens en el
    // storage correcto + limpiar el opuesto.
    this.authService.login(this.loginForm.value, this.isStorage).subscribe({
      next: () => {
        setTimeout(() => {
          this.isLoading = false;

          const intendedRedirect = sessionStorage.getItem(
            STORAGE_KEYS.REDIRECT_AFTER_LOGIN,
          );
          sessionStorage.removeItem(STORAGE_KEYS.REDIRECT_AFTER_LOGIN);
          if (intendedRedirect) {
            this.router.navigateByUrl(intendedRedirect);
            return;
          }

          // Después del login, this.isStorage define dónde se guardaron
          // los flags. Leemos profile_complete desde ahí — no del
          // valor cached de this.storage (que ya no usamos).
          const storage: 'session' | 'local' = this.isStorage ? 'local' : 'session';
          const profileComplete =
            this.storageMethod.getStorageItem(
              storage,
              STORAGE_KEYS.PROFILE_COMPLETE,
            ) === 'true';
          this.router.navigate([profileComplete ? '/dashboard' : '/profile']);
        }, 400);
      },
      error: (err: HttpErrorResponse) => {
        this.isLoading = false;
        this.errorMessage = 'Credenciales inválidas. Intentalo nuevamente.';
        console.error('Login error:', err);
      },
    });
  }

  /**
   * Toggles password visibility
   */
  togglePasswordVisibility(): void {
    this.showPassword = !this.showPassword;
  }
}

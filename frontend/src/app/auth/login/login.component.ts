import { Component } from '@angular/core';
import { AuthService } from '../auth.service';
import { CommonModule } from '@angular/common';
import { Title } from '@angular/platform-browser';
import { Router, RouterModule } from '@angular/router';
import { StorageMethodComponent } from '../../shared/storage-method/storage-method';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { HttpErrorResponse } from '@angular/common/http';
import { STORAGE_KEYS } from '../../constants/app-stats';

/**
 * Login component for user authentication
 */
@Component({
  selector: 'app-login',
  imports: [CommonModule, ReactiveFormsModule, RouterModule],
  standalone: true,
  templateUrl: './login.component.html',
  styleUrls: ['./login.component.scss']
})
export class LoginComponent {
  loginForm!: FormGroup;
  isLoading = false;
  errorMessage = '';
  isStorage = false;
  storage: 'session' | 'local' = 'session';
  showPassword = false;

  constructor(
    private fb: FormBuilder,
    private authService: AuthService,
    private router: Router,
    private titleService: Title,
    private storageMethod: StorageMethodComponent
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
      password: ['', Validators.required]
    });
  }

  /**
   * Loads storage preference from localStorage
   */
  private loadStoragePreference(): void {
    if (localStorage.getItem(STORAGE_KEYS.STORAGE_PREFERENCE) === 'true') {
      this.isStorage = true;
      this.storage = 'local';
    }
  }

  /**
   * Toggles storage preference between session and local storage
   */
  toggleStorage(): void {
    this.isStorage = !this.isStorage;
    if (this.isStorage) {
      localStorage.setItem(STORAGE_KEYS.STORAGE_PREFERENCE, 'true');
      this.storage = 'local';
    } else {
      localStorage.setItem(STORAGE_KEYS.STORAGE_PREFERENCE, 'false');
      this.storage = 'session';
    }
  }

  /**
   * Handles form submission and login process
   */
  onSubmit(): void {
    if (this.loginForm.invalid) return;

    this.isLoading = true;
    this.authService.login(this.loginForm.value).subscribe({
      next: () => {
        setTimeout(() => {
          this.isLoading = false;
          const redirectPath = sessionStorage.getItem(STORAGE_KEYS.REDIRECT_AFTER_LOGIN) || '';
          sessionStorage.removeItem(STORAGE_KEYS.REDIRECT_AFTER_LOGIN);

          if (this.storageMethod.getStorageItem(this.storage, STORAGE_KEYS.PROFILE_COMPLETE) === 'true') {
            this.router.navigate(['/results']);
          } else {
            this.router.navigate([redirectPath]);
          }
        }, 1200);
      },
      error: (err: HttpErrorResponse) => {
        this.isLoading = false;
        this.errorMessage = 'Credenciales inválidas. Intentalo nuevamente.';
        console.error('Login error:', err);
      }
    });
  }

  /**
   * Toggles password visibility
   */
  togglePasswordVisibility(): void {
    this.showPassword = !this.showPassword;
  }
}

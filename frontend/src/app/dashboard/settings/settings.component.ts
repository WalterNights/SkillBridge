import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { Title } from '@angular/platform-browser';

import { environment } from '../../../environment/environment';
import { AuthService } from '../../auth/auth.service';
import { StorageMethodComponent } from '../../shared/storage-method/storage-method';
import { SelectComponent, SelectOption } from '../../shared/select/select.component';
import { TwoFactorService } from '../../services/two-factor.service';
import { TwoFactorModalComponent } from './two-factor-modal.component';

/**
 * Configuración del usuario. Vive dentro del AppShell así que el
 * componente solo renderiza contenido — el sidebar y topbar los
 * provee el shell padre.
 *
 * Política dark-only: ya no exponemos toggle de modo claro. Toda la
 * UI vive en el canvas oscuro y los toggles legacy fueron removidos
 * para evitar arrastrar un modo que ya no soportamos.
 */
@Component({
  selector: 'app-settings',
  standalone: true,
  imports: [CommonModule, FormsModule, SelectComponent, TwoFactorModalComponent],
  templateUrl: './settings.component.html',
  styleUrls: ['./settings.component.scss'],
})
export class SettingsComponent implements OnInit {
  private router = inject(Router);
  private authService = inject(AuthService);
  private storageMethod = inject(StorageMethodComponent);
  private titleService = inject(Title);
  private http = inject(HttpClient);

  userName: string | null = null;
  userEmail: string | null = null;
  storage: 'session' | 'local' = 'session';

  enableNotifications = true;
  enableEmailAlerts = true;
  language = 'es';
  /** Catálogo de idiomas — usado por el dropdown custom. */
  languageOptions: SelectOption[] = [
    { value: 'es', label: 'Español' },
    { value: 'en', label: 'English' },
    { value: 'pt', label: 'Português' },
  ];

  /** ID del UserProfile cargado — necesario para el PATCH. */
  private profileId: number | null = null;
  isSaving = false;
  saveStatus: 'idle' | 'success' | 'error' = 'idle';
  saveErrorMsg = '';

  // 2FA state — toggle visible refleja el flag del backend. Modal se
  // abre al click del toggle (en cualquier sentido) y emite el nuevo
  // estado al cerrar; recién ahí actualizamos `twoFactorEnabled`.
  twoFactorEnabled = false;
  twoFactorModalMode: 'enable' | 'disable' | null = null;
  private twoFactorService = inject(TwoFactorService);

  constructor() {
    this.titleService.setTitle('SkilTak — Configuración');
  }

  ngOnInit(): void {
    this.storage = localStorage.getItem('storage') === 'true' ? 'local' : 'session';
    this.authService.isLoggedIn$.subscribe(() => {
      this.userName = this.storageMethod.getStorageItem(this.storage, 'user_name');
      this.userEmail = this.storageMethod.getStorageItem(this.storage, 'user_email');
    });
    this.loadProfilePreferences();
    this.loadTwoFactorStatus();
  }

  private loadTwoFactorStatus(): void {
    this.twoFactorService.status().subscribe({
      next: (res) => (this.twoFactorEnabled = res.enabled),
      error: () => {
        /* Soft-fail: la sección 2FA queda como "no enabled". El user puede
         * intentar activar y si el backend está down recibirá error. */
      },
    });
  }

  openTwoFactorModal(): void {
    this.twoFactorModalMode = this.twoFactorEnabled ? 'disable' : 'enable';
  }

  closeTwoFactorModal(): void {
    this.twoFactorModalMode = null;
  }

  onTwoFactorChanged(enabled: boolean): void {
    this.twoFactorEnabled = enabled;
  }

  /** Carga el perfil para obtener `email_alerts_enabled` actual + el ID. */
  private loadProfilePreferences(): void {
    this.http.get<any>(`${environment.apiUrl}/users/profiles/`).subscribe({
      next: (res) => {
        const profile = Array.isArray(res?.results) ? res.results[0] : (Array.isArray(res) ? res[0] : res);
        if (profile && typeof profile === 'object') {
          this.profileId = profile.id ?? null;
          if (typeof profile.email_alerts_enabled === 'boolean') {
            this.enableEmailAlerts = profile.email_alerts_enabled;
          }
        }
      },
      error: () => {
        /* Si falla, dejamos los defaults — el user puede igual togglear
         * y el save va a fallar más tarde con un mensaje claro. */
      },
    });
  }

  saveSettings(): void {
    this.isSaving = true;
    this.saveStatus = 'idle';
    this.saveErrorMsg = '';
    // Usamos POST al collection (no PATCH /{id}/) porque el backend
    // tiene un upsert en UserProfileViewSet.create() — busca el profile
    // del request.user y hace partial_update si existe, sino crea. Así
    // evitamos depender de profileId que puede no estar cargado todavía
    // si loadProfilePreferences() todavía no terminó / falló.
    const payload = { email_alerts_enabled: this.enableEmailAlerts };
    this.http.post<any>(`${environment.apiUrl}/users/profiles/`, payload).subscribe({
      next: (res) => {
        this.isSaving = false;
        this.saveStatus = 'success';
        // Captura el id para futuras llamadas (otros saves, 2FA, etc).
        if (res?.id) this.profileId = res.id;
        setTimeout(() => (this.saveStatus = 'idle'), 3000);
      },
      error: (err) => {
        this.isSaving = false;
        this.saveStatus = 'error';
        // Surface el detalle del backend para debug — útil para saber
        // si es validación, auth, etc. DRF devuelve `{detail: "..."}`
        // o un dict de field errors `{field: ["msg", ...]}`.
        const errorObj = err?.error;
        let detail = '';
        if (typeof errorObj === 'string') {
          detail = errorObj;
        } else if (errorObj?.detail) {
          detail = errorObj.detail;
        } else if (errorObj && typeof errorObj === 'object') {
          // dict de field errors → "field1: msg, field2: msg"
          detail = Object.entries(errorObj)
            .map(([k, v]) => `${k}: ${Array.isArray(v) ? v.join(', ') : v}`)
            .join(' · ');
        }
        const httpStatus = err?.status ? ` (HTTP ${err.status})` : '';
        this.saveErrorMsg = detail
          ? `${detail}${httpStatus}`
          : `No pudimos guardar.${httpStatus}`;
        console.error('[settings] Error al guardar:', err);
        setTimeout(() => (this.saveStatus = 'idle'), 8000);
      },
    });
  }

  goBack(): void {
    this.router.navigate(['/dashboard']);
  }
}

import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { Title } from '@angular/platform-browser';

import { environment } from '../../../environment/environment';
import { AuthService } from '../../auth/auth.service';
import { StorageMethodComponent } from '../../shared/storage-method/storage-method';

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
  imports: [CommonModule, FormsModule],
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

  /** ID del UserProfile cargado — necesario para el PATCH. */
  private profileId: number | null = null;
  isSaving = false;
  saveStatus: 'idle' | 'success' | 'error' = 'idle';

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
    if (this.profileId === null) {
      this.saveStatus = 'error';
      return;
    }
    this.isSaving = true;
    this.saveStatus = 'idle';
    // PATCH parcial — solo enviamos los fields que el endpoint conoce.
    // `enableNotifications` (in-app) y `language` quedan como prefs locales
    // hasta que tengamos endpoints para ellos; no rompen el PATCH actual.
    const payload = { email_alerts_enabled: this.enableEmailAlerts };
    this.http
      .patch<any>(`${environment.apiUrl}/users/profiles/${this.profileId}/`, payload)
      .subscribe({
        next: () => {
          this.isSaving = false;
          this.saveStatus = 'success';
          setTimeout(() => (this.saveStatus = 'idle'), 3000);
        },
        error: () => {
          this.isSaving = false;
          this.saveStatus = 'error';
          setTimeout(() => (this.saveStatus = 'idle'), 5000);
        },
      });
  }

  goBack(): void {
    this.router.navigate(['/dashboard']);
  }
}

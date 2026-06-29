import { Component, inject } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { Title } from '@angular/platform-browser';

import { AuthService } from '../auth.service';
import { StorageMethodComponent } from '../../shared/storage-method/storage-method';
import { STORAGE_KEYS } from '../../constants/app-stats';

/**
 * /auth/linkedin/complete — destino del redirect post-OAuth.
 *
 * El backend (LinkedInCallbackView) redirige acá con:
 *   ?access=<jwt>&refresh=<jwt>     ← éxito
 *   ?error=<code>                   ← falla
 *
 * Levantamos los tokens del query string, los guardamos en
 * sessionStorage (NO localStorage — el OAuth flow asume "una sesión",
 * el user puede tildar "remember me" en próximos logins normales),
 * y redirigimos a /dashboard o /profile según corresponda.
 *
 * Limpiamos el query string al final para que los tokens no queden
 * visibles en la barra del browser ni en logs de navegación.
 */
@Component({
  selector: 'app-linkedin-complete',
  standalone: true,
  template: `
    <div class="min-h-screen flex items-center justify-center px-6 bg-canvas">
      <div class="text-center max-w-md">
        <div class="loader-ring mx-auto mb-6"></div>
        <p class="text-bone text-body-lg font-semibold mb-2">
          {{ statusMessage }}
        </p>
        @if (errorDetail) {
          <p class="text-sm text-warm-grey">{{ errorDetail }}</p>
        }
      </div>
    </div>
  `,
  styles: [
    `
      .loader-ring {
        width: 36px;
        height: 36px;
        border: 3px solid rgba(249, 115, 22, 0.2);
        border-top-color: #f97316;
        border-radius: 50%;
        animation: spin 800ms linear infinite;
      }
      @keyframes spin {
        to {
          transform: rotate(360deg);
        }
      }
    `,
  ],
})
export class LinkedinCompleteComponent {
  statusMessage = 'Completando inicio de sesión…';
  errorDetail = '';

  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private auth = inject(AuthService);
  private storageMethod = inject(StorageMethodComponent);
  private titleService = inject(Title);

  constructor() {
    this.titleService.setTitle('SkilTak — Conectando con LinkedIn');
    this.handleCallback();
  }

  private handleCallback(): void {
    const params = this.route.snapshot.queryParamMap;
    const error = params.get('error');
    if (error) {
      this.statusMessage = 'No pudimos conectar con LinkedIn';
      this.errorDetail = this.friendlyError(error);
      // Redirigimos al login después de 3s para que el user vea el mensaje
      setTimeout(() => this.router.navigate(['/auth/login']), 3000);
      return;
    }

    const accessToken = params.get('access');
    const refreshToken = params.get('refresh');
    if (!accessToken || !refreshToken) {
      this.statusMessage = 'Respuesta incompleta de LinkedIn';
      setTimeout(() => this.router.navigate(['/auth/login']), 2000);
      return;
    }

    // OAuth flow asume una sesión activa solamente — sessionStorage.
    // Si el user quiere "remember me" persistente, puede loguear con
    // password normal con el switch tildado después.
    this.storageMethod.setStorageItem('session', STORAGE_KEYS.ACCESS_TOKEN, accessToken);
    this.storageMethod.setStorageItem('session', STORAGE_KEYS.REFRESH_TOKEN, refreshToken);
    // Limpiar el flag de storage por las dudas — OAuth = sessionStorage.
    localStorage.removeItem(STORAGE_KEYS.STORAGE_PREFERENCE);

    this.auth.syncAuthStatus();
    this.auth.updateProfileStatus();

    // Limpiamos el query string. Las navegaciones siguientes ya no
    // exponen los tokens.
    window.history.replaceState({}, '', '/auth/linkedin/complete');

    // Decidir destino — primer login OAuth siempre va a /profile
    // (LinkedIn solo nos dio nombre + email, falta city/título/skills).
    // Subsecuentes con perfil completo van a /dashboard.
    const profileComplete =
      this.storageMethod.getStorageItem('session', STORAGE_KEYS.PROFILE_COMPLETE) === 'true';
    this.router.navigate([profileComplete ? '/dashboard' : '/profile']);
  }

  private friendlyError(code: string): string {
    const mapping: Record<string, string> = {
      user_cancelled_login: 'Cancelaste el ingreso. Puedes intentar de nuevo cuando quieras.',
      invalid_state: 'La solicitud expiró. Intenta de nuevo.',
      missing_params: 'LinkedIn no envió toda la información esperada.',
      token_exchange_failed: 'LinkedIn rechazó la autorización. Intenta de nuevo.',
      no_access_token: 'No recibimos el token de LinkedIn. Intenta de nuevo.',
      userinfo_failed: 'No pudimos leer tu perfil de LinkedIn.',
      incomplete_userinfo: 'LinkedIn no devolvió tu correo. Asegúrate de tenerlo verificado.',
      linkedin_unreachable: 'LinkedIn no respondió. Intenta en unos minutos.',
      linkedin_oauth_not_configured: 'El login con LinkedIn no está disponible en este momento.',
    };
    return mapping[code] ?? 'Hubo un problema con el login de LinkedIn.';
  }
}

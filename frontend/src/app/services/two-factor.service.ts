import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { environment } from '../../environment/environment';

export interface TwoFactorStatus {
  enabled: boolean;
}

export interface TwoFactorSetupResponse {
  secret: string;
  qr_data_url: string;
  otpauth_uri: string;
}

/**
 * Service para 2FA TOTP.
 *
 * Endpoints backend:
 *   - GET  /api/users/2fa/status/       → ¿activo?
 *   - POST /api/users/2fa/setup/        → genera secret + QR
 *   - POST /api/users/2fa/activate/     → body {code}, activa
 *   - POST /api/users/2fa/disable/      → body {code}, desactiva
 *
 * El flow del frontend:
 *   1. status() → ver si ya está activo
 *   2. Si NO → setup() → mostrar QR → user lo escanea → activate(code)
 *   3. Si SÍ → user quiere desactivar → disable(code)
 */
@Injectable({ providedIn: 'root' })
export class TwoFactorService {
  private http = inject(HttpClient);
  private base = `${environment.apiUrl}/users/2fa`;

  status(): Observable<TwoFactorStatus> {
    return this.http.get<TwoFactorStatus>(`${this.base}/status/`);
  }

  setup(): Observable<TwoFactorSetupResponse> {
    return this.http.post<TwoFactorSetupResponse>(`${this.base}/setup/`, {});
  }

  activate(code: string): Observable<TwoFactorStatus> {
    return this.http.post<TwoFactorStatus>(`${this.base}/activate/`, { code });
  }

  disable(code: string): Observable<TwoFactorStatus> {
    return this.http.post<TwoFactorStatus>(`${this.base}/disable/`, { code });
  }
}

import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';

import { environment } from '../../environment/environment';

/**
 * Llamadas al backend relacionadas con el perfil del usuario autenticado.
 *
 * El token JWT se inyecta automáticamente via `TokenInterceptor` —
 * los componentes no necesitan armar headers a mano.
 */
@Injectable({ providedIn: 'root' })
export class ProfileService {
  constructor(private http: HttpClient) {}

  /**
   * Devuelve el perfil del usuario autenticado. El endpoint del backend
   * filtra por `request.user`, por eso siempre devuelve uno solo (o vacío).
   */
  getMyProfile(): Observable<any> {
    return this.http.get<any>(`${environment.apiUrl}/users/profiles/`);
  }
}

import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { environment } from '../../environment/environment';

export interface QuantifySuggestionsResponse {
  suggestions: string[];
}

/**
 * Service para la feature "Cuantificar logros del CV".
 *
 * Endpoint backend: POST /api/users/cv/quantify/
 * Toma un bullet de experiencia + contexto del rol y devuelve 3
 * reescrituras con números/métricas. NO persiste — la decisión de
 * aplicar la sugerencia es del user (vía PATCH al profile).
 */
@Injectable({ providedIn: 'root' })
export class QuantifyService {
  private http = inject(HttpClient);
  private url = `${environment.apiUrl}/users/cv/quantify/`;

  suggest(
    text: string,
    roleTitle = '',
    company = '',
  ): Observable<QuantifySuggestionsResponse> {
    return this.http.post<QuantifySuggestionsResponse>(this.url, {
      text,
      role_title: roleTitle,
      company,
    });
  }
}

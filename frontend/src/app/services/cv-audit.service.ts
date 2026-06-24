import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { environment } from '../../environment/environment';

export type AuditSeverity = 'ok' | 'warning' | 'critical';

export interface AuditCategory {
  /** Identificador estable (summary, experience, skills, education, contact, length). */
  key: string;
  /** Label legible para la UI. */
  label: string;
  severity: AuditSeverity;
  message: string;
}

export interface CvAuditResponse {
  /** Score holístico 0-100. */
  score: number;
  /** Resumen de 1-2 oraciones del estado general. */
  overall: string;
  categories: AuditCategory[];
  /** Top 3 recomendaciones priorizadas (las más impactantes). */
  top_recommendations: string[];
}

/**
 * Service para la feature "Auditar mi CV con AI".
 *
 * Endpoint backend: POST /api/users/cv/audit/
 * Sin body — usa el perfil del user autenticado.
 *
 * Rate-limit del backend: 10/h por user. El frontend cachea el último
 * resultado en memoria por session para evitar regenerar al cerrar
 * y reabrir el modal accidentalmente.
 */
@Injectable({ providedIn: 'root' })
export class CvAuditService {
  private http = inject(HttpClient);
  private url = `${environment.apiUrl}/users/cv/audit/`;

  audit(): Observable<CvAuditResponse> {
    return this.http.post<CvAuditResponse>(this.url, {});
  }
}

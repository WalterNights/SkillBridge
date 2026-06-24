import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { environment } from '../../environment/environment';

/**
 * Shape de la respuesta del endpoint /api/users/cv/improve/.
 *
 * Solo trae los campos que el AI propone reescribir — el caller hace
 * merge con el profile original al persistir (no se tocan datos no
 * mejorables como nombre, fechas, ubicación).
 */
export interface CvImproveResponse {
  professional_title: string;
  summary: string;
  skills: string;
  soft_skills: string;
  experience: Array<{
    company: string;
    position: string;
    start_date: string;
    end_date: string;
    location_city?: string;
    location_country?: string;
    description: string;
  }>;
}

/**
 * Service para 'Mejorar mi CV con AI'.
 *
 * El endpoint del backend NO persiste — devuelve la propuesta. La UI
 * se encarga de mostrarla, pedir confirmación, y luego hacer PATCH al
 * profile con los campos que el user acepta.
 *
 * Rate-limit del backend: 5/hora por user (rewrite del CV completo
 * cuesta tokens, no queremos farmearlo).
 */
@Injectable({ providedIn: 'root' })
export class CvImproveService {
  private http = inject(HttpClient);
  private url = `${environment.apiUrl}/users/cv/improve/`;

  improve(): Observable<CvImproveResponse> {
    return this.http.post<CvImproveResponse>(this.url, {});
  }
}

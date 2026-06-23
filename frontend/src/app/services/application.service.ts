import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { environment } from '../../environment/environment';
import { JobOffer } from '../models/job-offer.model';

export type ApplicationStatus = 'pending' | 'applied';

export interface JobApplicationDto {
  id: number;
  offer: JobOffer;
  status: ApplicationStatus;
  clicked_at: string;
  applied_at: string | null;
}

/**
 * Service para el modelo JobApplication del backend.
 *
 * Flow desde el job-detail:
 *   1. User clickea "Aplicar en X" → tab nueva al portal + `create()`
 *      (status=pending).
 *   2. La card cambia al modo "¿Aplicaste?" — Sí → `confirm(id)`,
 *      No → `delete(id)` (undo).
 *
 * El badge "Aplicado" del feed usa `appliedOfferIds()` que devuelve
 * solo IDs (payload mínimo), el frontend hace un Set en memoria para
 * lookup O(1).
 */
@Injectable({ providedIn: 'root' })
export class ApplicationService {
  private http = inject(HttpClient);
  private base = `${environment.apiUrl}/applications`;

  list(): Observable<JobApplicationDto[]> {
    return this.http.get<JobApplicationDto[]>(`${this.base}/`);
  }

  /** Idempotente: si ya existe para (user, offer) devuelve la existente. */
  create(offerId: number): Observable<JobApplicationDto> {
    return this.http.post<JobApplicationDto>(`${this.base}/`, { offer_id: offerId });
  }

  confirm(applicationId: number): Observable<JobApplicationDto> {
    return this.http.post<JobApplicationDto>(`${this.base}/${applicationId}/confirm/`, {});
  }

  delete(applicationId: number): Observable<void> {
    return this.http.delete<void>(`${this.base}/${applicationId}/`);
  }

  /** Set de offer_ids con status=applied — usado por el feed para el badge. */
  appliedOfferIds(): Observable<{ applied_offer_ids: number[] }> {
    return this.http.get<{ applied_offer_ids: number[] }>(`${this.base}/applied-ids/`);
  }
}

import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { environment } from '../../environment/environment';
import { JobOffer } from '../models/job-offer.model';

export type ApplicationStatus =
  | 'pending'
  | 'applied'
  | 'in_review'
  | 'interview'
  | 'offer'
  | 'rejected'
  | 'withdrawn';

export interface JobApplicationDto {
  id: number;
  offer: JobOffer;
  status: ApplicationStatus;
  clicked_at: string;
  applied_at: string | null;
  status_changed_at: string | null;
  notes: string;
}

export interface StatusOption {
  value: ApplicationStatus;
  label: string;
}

export interface StatusOptionsResponse {
  options: StatusOption[];
  /** Estados que cuentan como "activos" — usado para tab "Activas". */
  active_statuses: ApplicationStatus[];
}

/**
 * Service para el modelo JobApplication del backend.
 *
 * Flow desde el job-detail:
 *   1. User clickea "Aplicar en X" → tab nueva al portal + `create()`
 *      (status=pending).
 *   2. La card cambia al modo "¿Aplicaste?" — Sí → `confirm(id)`,
 *      No → `delete(id)` (undo).
 *   3. Después, el user puede mover entre estados en /applications
 *      via `updateStatus(id, status)` — interview, offer, rejected, etc.
 *
 * El badge "Aplicado" del feed usa `appliedOfferIds()` que devuelve
 * solo IDs (payload mínimo), el frontend hace un Set en memoria para
 * lookup O(1).
 */
@Injectable({ providedIn: 'root' })
export class ApplicationService {
  private http = inject(HttpClient);
  private base = `${environment.apiUrl}/applications`;

  /** @param filter `'active'` para excluir cerradas, o un status puntual. */
  list(filter?: 'active' | ApplicationStatus): Observable<JobApplicationDto[]> {
    let url = `${this.base}/`;
    if (filter === 'active') {
      url += '?active=true';
    } else if (filter) {
      url += `?status=${filter}`;
    }
    return this.http.get<JobApplicationDto[]>(url);
  }

  /** Idempotente: si ya existe para (user, offer) devuelve la existente. */
  create(offerId: number): Observable<JobApplicationDto> {
    return this.http.post<JobApplicationDto>(`${this.base}/`, { offer_id: offerId });
  }

  confirm(applicationId: number): Observable<JobApplicationDto> {
    return this.http.post<JobApplicationDto>(`${this.base}/${applicationId}/confirm/`, {});
  }

  /** Mover la postulación entre estados (interview, offer, rejected, etc.) */
  updateStatus(applicationId: number, status: ApplicationStatus): Observable<JobApplicationDto> {
    return this.http.post<JobApplicationDto>(
      `${this.base}/${applicationId}/update-status/`,
      { status },
    );
  }

  /** PATCH editable — por ahora solo `notes`. */
  updateNotes(applicationId: number, notes: string): Observable<JobApplicationDto> {
    return this.http.patch<JobApplicationDto>(`${this.base}/${applicationId}/`, { notes });
  }

  delete(applicationId: number): Observable<void> {
    return this.http.delete<void>(`${this.base}/${applicationId}/`);
  }

  /** Set de offer_ids con status=applied — usado por el feed para el badge. */
  appliedOfferIds(): Observable<{ applied_offer_ids: number[] }> {
    return this.http.get<{ applied_offer_ids: number[] }>(`${this.base}/applied-ids/`);
  }

  /** Catálogo de status válidos — para el dropdown del front. */
  statusOptions(): Observable<StatusOptionsResponse> {
    return this.http.get<StatusOptionsResponse>(`${this.base}/status-options/`);
  }
}

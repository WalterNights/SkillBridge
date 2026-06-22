import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { environment } from '../../environment/environment';

export type NotificationKind = 'match' | 'reminder' | 'system';
export type NotificationTab = 'unread' | 'read' | 'saved';

export interface NotificationDto {
  id: number;
  kind: NotificationKind;
  title: string;
  body: string;
  is_read: boolean;
  is_saved: boolean;
  metadata: Record<string, unknown>;
  created_at: string;
}

/**
 * HTTP service para el modelo Notification del backend.
 *
 * El drawer del user-nav lo consume desde signals — no expone state
 * propio acá. Si en el futuro queremos polling o invalidación cruzada
 * (ej. el scrape crea notifs y queremos refrescar el bell sin click),
 * se agrega un BehaviorSubject acá.
 */
@Injectable({ providedIn: 'root' })
export class NotificationService {
  private http = inject(HttpClient);
  private base = `${environment.apiUrl}/notifications`;

  list(tab?: NotificationTab): Observable<NotificationDto[]> {
    const url = tab ? `${this.base}/?status=${tab}` : `${this.base}/`;
    return this.http.get<NotificationDto[]>(url);
  }

  markRead(id: number): Observable<NotificationDto> {
    return this.http.post<NotificationDto>(`${this.base}/${id}/mark-read/`, {});
  }

  toggleSave(id: number): Observable<NotificationDto> {
    return this.http.post<NotificationDto>(`${this.base}/${id}/toggle-save/`, {});
  }

  markAllRead(): Observable<{ updated: number }> {
    return this.http.post<{ updated: number }>(`${this.base}/mark-all-read/`, {});
  }
}

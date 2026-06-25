import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { environment } from '../../environment/environment';
import { PaginatedResponse } from '../models/paginated-response.model';

export interface FaqCategory {
  id: number;
  name: string;
  slug: string;
  description: string;
  display_order: number;
}

export interface FaqEntry {
  id: number;
  question: string;
  answer: string;
  category: FaqCategory | null;
  display_order: number;
  view_count: number;
  created_at: string;
  updated_at: string;
}

/** Respuesta del POST /api/faq/ask/ — incluye el draft AI o un flag
 *  que indica que la AI no pudo responder esta vez. */
export interface FaqAskResponse {
  id: number;
  question: string;
  ai_answer: string;
  has_ai_answer: boolean;
  detail: string;
}

/** Vista admin con todos los metadatos de moderación. */
export interface FaqAdminEntry extends FaqEntry {
  ai_draft: string;
  source: 'seed' | 'user';
  status: 'pending' | 'published' | 'rejected';
  submitted_by: number | null;
  submitted_by_username: string;
  moderated_by: number | null;
  moderated_by_username: string;
  moderated_at: string | null;
  moderation_note: string;
}

export interface FaqAdminUpdate {
  question?: string;
  answer?: string;
  category_id?: number | null;
  status?: 'pending' | 'published' | 'rejected';
  moderation_note?: string;
  display_order?: number;
}

export interface FaqAdminStats {
  totals: { all: number; pending: number; published: number; rejected: number };
  approval_rate_pct: number;
  by_category: { category__name: string; category__slug: string; count: number }[];
  by_source: { source: string; count: number }[];
  recent_user_questions: {
    id: number;
    question: string;
    status: string;
    created_at: string;
  }[];
}

/**
 * Cliente del backend FAQ. Endpoints públicos son anónimos; `ask()`
 * exige token JWT; los admin* exigen además is_staff (gated por
 * `IsAdminUser` en el server — el frontend hace su propio AdminGuard).
 */
@Injectable({ providedIn: 'root' })
export class FaqService {
  private http = inject(HttpClient);
  private base = `${environment.apiUrl}/faq`;

  listPublic(categorySlug?: string): Observable<FaqEntry[]> {
    const url = categorySlug
      ? `${this.base}/?category=${encodeURIComponent(categorySlug)}`
      : `${this.base}/`;
    return this.http.get<FaqEntry[]>(url);
  }

  listCategories(): Observable<FaqCategory[]> {
    return this.http.get<FaqCategory[]>(`${this.base}/categories/`);
  }

  /** Incrementa view_count cuando el user expande una FAQ. Errores
   *  silenciosos — métrica no-crítica. */
  trackView(id: number): Observable<void> {
    return this.http.post<void>(`${this.base}/${id}/view/`, {});
  }

  ask(question: string): Observable<FaqAskResponse> {
    return this.http.post<FaqAskResponse>(`${this.base}/ask/`, { question });
  }

  // ─── Admin ─────────────────────────────────────────────────────────

  adminList(
    statusFilter: 'pending' | 'published' | 'rejected' | 'all' = 'pending',
    source?: 'user' | 'seed',
  ): Observable<PaginatedResponse<FaqAdminEntry>> {
    const params = new URLSearchParams({ status: statusFilter });
    if (source) params.set('source', source);
    return this.http.get<PaginatedResponse<FaqAdminEntry>>(
      `${this.base}/admin/?${params.toString()}`,
    );
  }

  adminUpdate(id: number, payload: FaqAdminUpdate): Observable<FaqAdminEntry> {
    return this.http.patch<FaqAdminEntry>(`${this.base}/admin/${id}/`, payload);
  }

  adminDelete(id: number): Observable<void> {
    return this.http.delete<void>(`${this.base}/admin/${id}/`);
  }

  adminStats(): Observable<FaqAdminStats> {
    return this.http.get<FaqAdminStats>(`${this.base}/admin/stats/`);
  }
}

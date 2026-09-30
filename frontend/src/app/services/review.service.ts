import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { environment } from '../../environment/environment';
import { PaginatedResponse } from '../models/paginated-response.model';

export type ReviewStatus = 'pending' | 'published' | 'rejected';

/** Reseña apta para el landing: aprobada, 4-5 estrellas y con
 *  consentimiento del usuario. Nombre ya abreviado por el backend. */
export interface LandingReview {
  id: number;
  rating: number;
  comment: string;
  name: string;
  role: string;
  city: string;
  photo_url: string | null;
}

export interface OwnReview {
  rating: number;
  comment: string;
  allow_public: boolean;
  status: ReviewStatus;
  moderation_note: string;
  created_at: string;
  updated_at: string;
}

/** GET/PUT /api/reviews/me/ — elegibilidad + la reseña del usuario. */
export interface MyReviewState {
  eligible: boolean;
  applications_count: number;
  min_applications: number;
  review: OwnReview | null;
}

export interface ReviewInput {
  rating: number;
  comment: string;
  allow_public: boolean;
}

export interface AdminReview {
  id: number;
  username: string;
  display_name: string;
  rating: number;
  comment: string;
  allow_public: boolean;
  /** Calculado por el backend: rating >= 4 y con consentimiento. */
  landing_eligible: boolean;
  status: ReviewStatus;
  moderation_note: string;
  moderated_by_username: string;
  moderated_at: string | null;
  created_at: string;
  updated_at: string;
}

/** Cliente de reseñas. `landing()` es anónimo; `me*` exige JWT; los
 *  admin* exigen además is_staff (IsAdminUser en el backend). */
@Injectable({ providedIn: 'root' })
export class ReviewService {
  private http = inject(HttpClient);
  private base = `${environment.apiUrl}/reviews`;

  landing(): Observable<LandingReview[]> {
    return this.http.get<LandingReview[]>(`${this.base}/landing/`);
  }

  getMine(): Observable<MyReviewState> {
    return this.http.get<MyReviewState>(`${this.base}/me/`);
  }

  saveMine(payload: ReviewInput): Observable<MyReviewState> {
    return this.http.put<MyReviewState>(`${this.base}/me/`, payload);
  }

  deleteMine(): Observable<void> {
    return this.http.delete<void>(`${this.base}/me/`);
  }

  // ─── Admin ─────────────────────────────────────────────────────────

  adminList(
    statusFilter: ReviewStatus | 'all' = 'pending',
  ): Observable<PaginatedResponse<AdminReview>> {
    return this.http.get<PaginatedResponse<AdminReview>>(`${this.base}/admin/`, {
      params: { status: statusFilter },
    });
  }

  adminUpdate(
    id: number,
    payload: { status: ReviewStatus; moderation_note?: string },
  ): Observable<AdminReview> {
    return this.http.patch<AdminReview>(`${this.base}/admin/${id}/`, payload);
  }
}

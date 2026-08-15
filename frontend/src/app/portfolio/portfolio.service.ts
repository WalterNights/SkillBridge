import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { environment } from '../../environment/environment';

/**
 * Shape del payload público que devuelve GET /api/portfolio/<slug>/.
 * Los tipos internos de `content` / `content_en` son intencionalmente
 * `unknown`: el shape del árbol es un contrato con el frontend y se
 * valida por uso (no en runtime). Si el editor manda basura, la
 * peor consecuencia es que el shell caiga al fallback estático.
 */
export interface PortfolioImage {
  id: number;
  project_id: string;
  url: string;
  alt_text: string;
  created_at: string;
}

export interface PortfolioPublicPayload {
  slug: string;
  content: Record<string, unknown>;
  content_en: Record<string, unknown>;
  images: PortfolioImage[];
}

export interface PortfolioAdminPayload extends PortfolioPublicPayload {
  created_at: string;
  updated_at: string;
}

export interface PortfolioUpdatePayload {
  content: Record<string, unknown>;
  content_en: Record<string, unknown>;
}

/**
 * Cliente del backend `portfolio`. Endpoints:
 *   - `GET  /api/portfolio/<slug>/`        público
 *   - `GET  /api/portfolio/<slug>/admin/`  IsAdminUser (metadata extra)
 *   - `PUT  /api/portfolio/<slug>/admin/`  IsAdminUser (sobreescribe)
 *   - `POST /api/portfolio/<slug>/images/` IsAdminUser (multipart)
 *   - `DELETE /api/portfolio/<slug>/images/<id>/` IsAdminUser
 *
 * El shell público consume `getPublic`; el editor consume el resto.
 */
@Injectable({ providedIn: 'root' })
export class PortfolioService {
  private http = inject(HttpClient);
  private base = `${environment.apiUrl}/portfolio`;

  getPublic(slug: string): Observable<PortfolioPublicPayload> {
    return this.http.get<PortfolioPublicPayload>(`${this.base}/${slug}/`);
  }

  getAdmin(slug: string): Observable<PortfolioAdminPayload> {
    return this.http.get<PortfolioAdminPayload>(`${this.base}/${slug}/admin/`);
  }

  updateAdmin(slug: string, payload: PortfolioUpdatePayload): Observable<PortfolioAdminPayload> {
    return this.http.put<PortfolioAdminPayload>(`${this.base}/${slug}/admin/`, payload);
  }

  uploadImage(
    slug: string,
    file: File,
    projectId: string,
    altText = '',
  ): Observable<PortfolioImage> {
    const form = new FormData();
    form.append('image', file);
    form.append('project_id', projectId);
    if (altText) form.append('alt_text', altText);
    return this.http.post<PortfolioImage>(`${this.base}/${slug}/images/`, form);
  }

  deleteImage(slug: string, imageId: number): Observable<void> {
    return this.http.delete<void>(`${this.base}/${slug}/images/${imageId}/`);
  }
}

import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { environment } from '../../environment/environment';

export type CoverLetterTone = 'formal' | 'cercano' | 'directo';
export type CoverLetterLanguage = 'es' | 'en';

export interface CoverLetterDto {
  id: number;
  offer: number | null;
  offer_title_snapshot: string;
  offer_company_snapshot: string;
  offer_url_snapshot: string;
  content: string;
  tone: CoverLetterTone;
  language: CoverLetterLanguage;
  user_edited: boolean;
  created_at: string;
  updated_at: string;
}

/**
 * Service para CoverLetter del backend.
 *
 * Flow desde el job-detail:
 *   1. User clickea "Generar carta" → `generate(offerId, tone, lang)`
 *      (POST genera con Gemini + persiste).
 *   2. Si ya existía para (user, offer) se sobreescribe. Frontend avisa
 *      al user si la anterior tenía `user_edited=true`.
 *   3. Modal muestra el texto; user puede editar inline → `updateContent`.
 *   4. Acciones: copiar al portapapeles, descargar PDF.
 */
@Injectable({ providedIn: 'root' })
export class CoverLetterService {
  private http = inject(HttpClient);
  private base = `${environment.apiUrl}/cover-letters`;

  /** Devuelve la carta existente para esta oferta, o `null` si no hay. */
  getForOffer(offerId: number): Observable<CoverLetterDto | null> {
    return new Observable((subscriber) => {
      this.http
        .get<CoverLetterDto[]>(`${this.base}/?job_offer_id=${offerId}`)
        .subscribe({
          next: (list) => {
            subscriber.next(list.length > 0 ? list[0] : null);
            subscriber.complete();
          },
          error: (err) => subscriber.error(err),
        });
    });
  }

  /** Genera + persiste. Si ya existía → sobreescribe. */
  generate(
    offerId: number,
    tone: CoverLetterTone,
    language: CoverLetterLanguage,
  ): Observable<CoverLetterDto> {
    return this.http.post<CoverLetterDto>(`${this.base}/`, {
      job_offer_id: offerId,
      tone,
      language,
    });
  }

  /** Guarda edición manual del user. Marca user_edited=true server-side. */
  updateContent(id: number, content: string): Observable<CoverLetterDto> {
    return this.http.patch<CoverLetterDto>(`${this.base}/${id}/`, { content });
  }

  delete(id: number): Observable<void> {
    return this.http.delete<void>(`${this.base}/${id}/`);
  }
}

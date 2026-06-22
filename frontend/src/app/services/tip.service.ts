import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable, of } from 'rxjs';
import { catchError, map } from 'rxjs/operators';

import { environment } from '../../environment/environment';
import { getTipOfTheDay as getStaticTipOfTheDay } from '../shell/daily-tips';

export interface TipDto {
  id: number;
  text: string;
  category: string;
  source: 'manual' | 'ai';
}

/**
 * Devuelve el "tip del día". Intenta el endpoint backend
 * (`/api/tips/today/`); si falla por red o status >= 400, cae al array
 * estático de daily-tips.ts. Resultado: el widget NUNCA se rompe, y
 * cuando el backend gana tips nuevos via la tarea semanal de Gemini,
 * los usuarios los ven automáticamente sin redeployar el frontend.
 *
 * El endpoint es AllowAny y devuelve el mismo tip para todos los users
 * en un día dado, así que cabe cachear el response en memoria del
 * service durante la sesión.
 */
@Injectable({ providedIn: 'root' })
export class TipService {
  private http = inject(HttpClient);
  private cache: string | null = null;
  private cacheDate: string | null = null;

  /**
   * @param profession Macro-categoría del usuario ('tech', 'design', 'marketing',
   *   'sales', 'finance', 'hr', 'operations', 'health', 'education', 'legal').
   *   Si se omite, el endpoint devuelve solo tips universales.
   *   El frontend infiere el valor con `inferProfessionCategory()`.
   */
  getTipOfTheDay(profession?: string): Observable<string> {
    const today = new Date().toISOString().slice(0, 10);
    const cacheKey = `${today}:${profession || 'all'}`;
    if (this.cache && this.cacheDate === cacheKey) {
      return of(this.cache);
    }
    const url = profession
      ? `${environment.apiUrl}/tips/today/?profession=${encodeURIComponent(profession)}`
      : `${environment.apiUrl}/tips/today/`;
    return this.http.get<TipDto>(url).pipe(
      map((dto) => {
        this.cache = dto.text;
        this.cacheDate = cacheKey;
        return dto.text;
      }),
      catchError(() => {
        // Fallback offline-first: el frontend tiene su propia copia de los
        // tips iniciales en daily-tips.ts (todos universales, sin filtro).
        const fallback = getStaticTipOfTheDay();
        this.cache = fallback;
        this.cacheDate = cacheKey;
        return of(fallback);
      }),
    );
  }
}

import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { NavigationEnd, Router } from '@angular/router';
import { Observable, filter } from 'rxjs';

import { environment } from '../../environment/environment';

/** Tipos soportados — debe matchear `EVENT_CHOICES` del backend. */
export type AnalyticsEventType = 'pageview' | 'cta_click' | 'outbound';

interface TrackPayload {
  event_type: AnalyticsEventType;
  path: string;
  label?: string;
  anon_id: string;
  referrer?: string;
}

/** Vista admin del /admin/stats — la shape la define backend SummaryView. */
export interface AnalyticsSummary {
  window_days: number;
  totals: {
    pageviews: number;
    unique_visitors: number;
    cta_clicks: number;
    outbound_clicks: number;
    authed_pageviews: number;
    anon_pageviews: number;
  };
  pageviews_by_day: { date: string; count: number }[];
  top_paths: { path: string; count: number }[];
  top_ctas: { label: string; count: number }[];
  top_referrers: { referrer: string; count: number }[];
}

const ANON_ID_KEY = 'analytics_anon_id';

/**
 * Cliente de analytics first-party.
 *
 * Funcionamiento:
 *   - Al construirse, se asegura un `anon_id` (UUID) persistente en
 *     localStorage. Si el user lo borra, lo regeneramos.
 *   - `init(router)` suscribe a NavigationEnd y dispara un pageview por
 *     cada ruta. Lo llamamos desde el bootstrap del root component.
 *   - `trackClick(label, opts?)` / `trackOutbound(label, opts?)`: helpers
 *     que se llaman desde templates `(click)="..."`.
 *   - Todos los POST son fire-and-forget — si el backend cae, no
 *     queremos romper el flow del user.
 *
 * Privacidad:
 *   - El anon_id NO es PII: es un UUID local. Sirve para contar
 *     visitantes únicos sin cookies.
 *   - En localhost (dev), se sigue tracking — útil para verificar
 *     la instrumentación. El backend filtra `localhost` de referrers
 *     en el summary.
 */
@Injectable({ providedIn: 'root' })
export class AnalyticsService {
  private http = inject(HttpClient);
  private baseUrl = `${environment.apiUrl}/analytics`;

  /** Track de si init() ya se llamó — evita doble-subscripción si el
   *  shell se recrea por re-bootstrap (no debería pasar pero es barato). */
  private initialized = false;
  private anonId: string;

  constructor() {
    this.anonId = this.ensureAnonId();
  }

  /** Suscribe a NavigationEnd para auto-trackear pageviews. Idempotente. */
  init(router: Router): void {
    if (this.initialized) return;
    this.initialized = true;
    router.events
      .pipe(filter((e): e is NavigationEnd => e instanceof NavigationEnd))
      .subscribe((event) => {
        // urlAfterRedirects refleja la URL final (sin la pre-redirect),
        // que es lo que el user realmente ve.
        this.trackPageview(event.urlAfterRedirects);
      });
  }

  /** Envía un pageview. Usable manualmente (ej. al abrir un modal que
   *  el user percibe como vista nueva). */
  trackPageview(path: string): void {
    this.send({
      event_type: 'pageview',
      path: this.normalizePath(path),
      anon_id: this.anonId,
      referrer: this.safeReferrer(),
    });
  }

  /** Click en CTA interno. Usar labels descriptivos y estables ya que
   *  el reporting agrupa por label exacto. */
  trackClick(label: string, opts?: { path?: string }): void {
    this.send({
      event_type: 'cta_click',
      path: this.normalizePath(opts?.path ?? this.currentPath()),
      label: label.slice(0, 80),
      anon_id: this.anonId,
    });
  }

  /** Click en link externo (postular en Computrabajo, perfil LinkedIn,
   *  etc.). El label debe identificar el destino conceptual, no el URL. */
  trackOutbound(label: string, opts?: { path?: string }): void {
    this.send({
      event_type: 'outbound',
      path: this.normalizePath(opts?.path ?? this.currentPath()),
      label: label.slice(0, 80),
      anon_id: this.anonId,
    });
  }

  /** Endpoint admin — devuelve el summary agregado. */
  getSummary(days: number = 30): Observable<AnalyticsSummary> {
    return this.http.get<AnalyticsSummary>(`${this.baseUrl}/summary/?days=${days}`);
  }

  // ─── Internals ──────────────────────────────────────────────────────

  private send(payload: TrackPayload): void {
    // No bloqueamos el llamador con `subscribe()` — fire-and-forget.
    // El backend silencia errores devolviendo 204 incluso en validation
    // fail, así que solo nos preocupan crashes de red (los ignoramos).
    this.http.post(`${this.baseUrl}/track/`, payload).subscribe({
      error: () => {
        /* swallow */
      },
    });
  }

  private ensureAnonId(): string {
    try {
      const existing = localStorage.getItem(ANON_ID_KEY);
      if (existing && existing.length >= 8) return existing;
      const fresh = this.generateUuid();
      localStorage.setItem(ANON_ID_KEY, fresh);
      return fresh;
    } catch {
      // Si localStorage no está disponible (Safari private mode, SSR),
      // generamos un id en memoria. Pierde la persistencia entre
      // navegaciones full-reload, pero no rompe nada.
      return this.generateUuid();
    }
  }

  private generateUuid(): string {
    if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
      return crypto.randomUUID();
    }
    // Fallback para entornos sin crypto.randomUUID (raro en 2026).
    return 'xxxxxxxxxxxx4xxxyxxxxxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
      const r = (Math.random() * 16) | 0;
      const v = c === 'x' ? r : (r & 0x3) | 0x8;
      return v.toString(16);
    });
  }

  private normalizePath(url: string): string {
    // Eliminamos el querystring y el fragment — bucketing por ruta lógica.
    const cleanPath = url.split('?')[0].split('#')[0];
    return cleanPath.startsWith('/') ? cleanPath : `/${cleanPath}`;
  }

  private currentPath(): string {
    if (typeof window === 'undefined') return '/';
    return window.location.pathname || '/';
  }

  private safeReferrer(): string {
    if (typeof document === 'undefined') return '';
    return (document.referrer || '').slice(0, 200);
  }
}

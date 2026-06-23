import { Injectable, computed, signal } from '@angular/core';

import { ScrapePortalStat } from './job.service';

export type ScrapeProgressState = 'idle' | 'loading' | 'success' | 'error';

export interface ScrapeProgressResult {
  newOffersCount: number;
  stats: Record<string, ScrapePortalStat>;
}

const _RECENT_DURATIONS_KEY = 'scrape_recent_durations_ms';
const _DEFAULT_DURATION_MS = 25_000; // 25s — fallback antes de tener historial
const _MAX_DURATION_HISTORY = 5;
const _ETA_TICK_INTERVAL_MS = 200;

/**
 * Estado global de la búsqueda de ofertas para el ScrapeProgressNotifier.
 *
 * El scrape es síncrono del lado backend (un POST que tarda 15-30s y
 * devuelve el resultado completo). No tenemos progreso real granular —
 * lo simulamos client-side basado en el tiempo esperado, suficiente
 * para UX. Si en el futuro convertimos el scrape a Celery + polling,
 * este service queda igual: solo cambiará quién lo alimenta.
 *
 * El ETA se calcula como el promedio de los últimos N scrapes
 * completados, guardado en localStorage. Más scrapes hacés, más
 * preciso queda.
 */
@Injectable({ providedIn: 'root' })
export class ScrapeProgressService {
  state = signal<ScrapeProgressState>('idle');
  /** Progreso 0-100. En `loading` se anima desde 0 hasta ~95 y se
   * clava ahí hasta que llega complete(); en success/error es 100. */
  progress = signal(0);
  /** Segundos restantes estimados. Se actualiza con tick. */
  etaSeconds = signal(0);
  /** Resultado final cuando state=success. */
  result = signal<ScrapeProgressResult | null>(null);
  /** Mensaje de error cuando state=error. */
  errorMessage = signal('');

  /** Para el botón "Cargando..." del trigger — true en loading. */
  isLoading = computed(() => this.state() === 'loading');

  private tickHandle: ReturnType<typeof setInterval> | null = null;
  private startedAtMs = 0;
  private expectedDurationMs = _DEFAULT_DURATION_MS;

  start(): void {
    this.cleanupTick();
    this.state.set('loading');
    this.progress.set(0);
    this.result.set(null);
    this.errorMessage.set('');
    this.startedAtMs = performance.now();
    this.expectedDurationMs = this.estimateDurationMs();
    this.etaSeconds.set(Math.ceil(this.expectedDurationMs / 1000));
    // Animación de progreso: tick cada 200ms.
    this.tickHandle = setInterval(() => this.tick(), _ETA_TICK_INTERVAL_MS);
  }

  complete(result: ScrapeProgressResult): void {
    this.cleanupTick();
    this.recordDuration(performance.now() - this.startedAtMs);
    this.progress.set(100);
    this.etaSeconds.set(0);
    this.result.set(result);
    this.state.set('success');
  }

  fail(message: string): void {
    this.cleanupTick();
    this.progress.set(100);
    this.etaSeconds.set(0);
    this.errorMessage.set(message);
    this.state.set('error');
  }

  /** Dismiss explícito por el user — solo permitido en success/error. */
  dismiss(): void {
    if (this.state() === 'loading') return;
    this.state.set('idle');
    this.progress.set(0);
    this.result.set(null);
    this.errorMessage.set('');
  }

  // ----------------------------------------------------------------

  private tick(): void {
    const elapsed = performance.now() - this.startedAtMs;
    const ratio = elapsed / this.expectedDurationMs;
    // Curva logarítmica: rápido al inicio, frena cerca del final.
    // Capeado a 95% en loading — el salto a 100% lo da complete().
    const eased = 1 - Math.exp(-2.5 * ratio);
    const pct = Math.min(95, Math.round(eased * 100));
    this.progress.set(pct);
    const remainingMs = Math.max(0, this.expectedDurationMs - elapsed);
    this.etaSeconds.set(Math.ceil(remainingMs / 1000));
  }

  private cleanupTick(): void {
    if (this.tickHandle !== null) {
      clearInterval(this.tickHandle);
      this.tickHandle = null;
    }
  }

  private estimateDurationMs(): number {
    const stored = this.loadRecentDurations();
    if (stored.length === 0) return _DEFAULT_DURATION_MS;
    // Promedio simple — alguno alto/bajo no rompe el ETA cuando hay 5.
    const avg = stored.reduce((s, v) => s + v, 0) / stored.length;
    return Math.round(avg);
  }

  private recordDuration(durationMs: number): void {
    // Filtro defensivo: ignorar valores ridículos (<2s = error, >120s = stuck).
    if (durationMs < 2000 || durationMs > 120000) return;
    const stored = this.loadRecentDurations();
    stored.push(Math.round(durationMs));
    while (stored.length > _MAX_DURATION_HISTORY) stored.shift();
    try {
      localStorage.setItem(_RECENT_DURATIONS_KEY, JSON.stringify(stored));
    } catch {
      /* QuotaExceeded o no-storage env: best-effort. */
    }
  }

  private loadRecentDurations(): number[] {
    try {
      const raw = localStorage.getItem(_RECENT_DURATIONS_KEY);
      if (!raw) return [];
      const parsed = JSON.parse(raw);
      return Array.isArray(parsed) ? parsed.filter((n) => typeof n === 'number') : [];
    } catch {
      return [];
    }
  }
}

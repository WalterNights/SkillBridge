import { CommonModule } from '@angular/common';
import { Component, computed, inject, signal } from '@angular/core';
import { animate, style, transition, trigger } from '@angular/animations';

import { ScrapeProgressService } from '../../services/scrape-progress.service';

/**
 * Notifier bottom-right que reemplaza los toasts de scrape.
 *
 * State machine guiada por `ScrapeProgressService`:
 *   - idle: oculto
 *   - loading: card expandida con barra de progreso, ETA, sin dismiss
 *   - success/error: card con el resultado, dismissable
 *
 * Plegado: en cualquier estado salvo idle el user puede colapsar a un
 * pill. Mientras está colapsado y en loading, el pill mantiene la
 * barrita de progreso en miniatura.
 *
 * El service se mantiene en idle hasta que `results.component` llama
 * a `start()` cuando dispara el scrape.
 */
@Component({
  selector: 'app-scrape-notifier',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './scrape-notifier.component.html',
  styleUrl: './scrape-notifier.component.scss',
  animations: [
    trigger('slideIn', [
      transition(':enter', [
        style({ opacity: 0, transform: 'translateY(20px) scale(0.95)' }),
        animate(
          '320ms cubic-bezier(0.22, 1, 0.36, 1)',
          style({ opacity: 1, transform: 'translateY(0) scale(1)' }),
        ),
      ]),
      transition(':leave', [
        animate(
          '220ms cubic-bezier(0.4, 0, 1, 1)',
          style({ opacity: 0, transform: 'translateY(20px) scale(0.95)' }),
        ),
      ]),
    ]),
  ],
})
export class ScrapeNotifierComponent {
  private progress = inject(ScrapeProgressService);

  state = this.progress.state;
  progressPct = this.progress.progress;
  etaSec = this.progress.etaSeconds;
  result = this.progress.result;
  errorMessage = this.progress.errorMessage;

  collapsed = signal(false);

  /** Visible cuando el service salió de idle. */
  visible = computed(() => this.state() !== 'idle');

  /** Líneas del breakdown de portales para mostrar en el resultado. */
  portalBreakdown = computed(() => {
    const r = this.result();
    if (!r) return [];
    return Object.entries(r.stats).map(([portal, s]) => ({
      portal,
      found: s.found,
      savedNew: s.saved_new,
      error: s.error,
    }));
  });

  /** Texto del header según el estado. */
  headerText = computed(() => {
    switch (this.state()) {
      case 'loading':
        return 'Buscando ofertas';
      case 'success':
        return '¡Búsqueda completa!';
      case 'error':
        return 'Algo falló';
      default:
        return '';
    }
  });

  /** Subtexto del header (ETA en loading, resumen en success). */
  subText = computed(() => {
    if (this.state() === 'loading') {
      const eta = this.etaSec();
      if (eta <= 0) return 'Casi listo…';
      if (eta === 1) return 'Falta menos de 1s…';
      return `Tiempo estimado: ${eta}s`;
    }
    if (this.state() === 'success') {
      const n = this.result()?.newOffersCount ?? 0;
      if (n === 0) return 'Sin ofertas nuevas esta vez';
      if (n === 1) return 'Se agregó 1 oferta nueva';
      return `Se agregaron ${n} ofertas nuevas`;
    }
    if (this.state() === 'error') {
      return this.errorMessage();
    }
    return '';
  });

  toggleCollapse(): void {
    this.collapsed.update((c) => !c);
  }

  /** Solo permitido en success/error — durante loading el dismiss está bloqueado. */
  onDismiss(): void {
    this.progress.dismiss();
    this.collapsed.set(false); // reset para próxima vez
  }

  canDismiss(): boolean {
    return this.state() !== 'loading';
  }
}

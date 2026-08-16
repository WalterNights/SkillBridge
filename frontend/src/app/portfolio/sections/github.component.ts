import { Component, OnInit, computed, inject, signal } from '@angular/core';

import {
  GithubContribution,
  GithubContributionsPayload,
  PortfolioService,
} from '../portfolio.service';
import { PortfolioI18nService } from '../i18n/portfolio-i18n.service';

const PORTFOLIO_SLUG = 'walternightsdev';

interface WeekColumn {
  /** 7 slots (Sun→Sat). null = celda vacía (padding al inicio/fin del año). */
  days: (GithubContribution | null)[];
}

interface MonthLabel {
  /** Índice de la semana (columna) donde arranca el mes. */
  weekIndex: number;
  /** Etiqueta corta: "Jan", "Feb"... */
  label: string;
}

/**
 * Widget de contribución en GitHub — heatmap 53 semanas × 7 días,
 * paleta naranja SkilTak. Diseñado para embeberse dentro de otras
 * secciones (hoy dentro del hero, debajo de los CTAs).
 *
 * Se oculta silenciosamente si el backend responde 404 (sin link de
 * GitHub configurado) o 502 (API externa caída) — nunca rompe el
 * layout de su contenedor.
 */
@Component({
  selector: 'app-github-section',
  standalone: true,
  imports: [],
  templateUrl: './github.component.html',
  styleUrl: './github.component.scss',
})
export class GithubSectionComponent implements OnInit {
  readonly i18n = inject(PortfolioI18nService);
  private readonly api = inject(PortfolioService);

  readonly loading = signal<boolean>(true);
  /** Payload del backend. null = todavía cargando o falló. */
  readonly payload = signal<GithubContributionsPayload | null>(null);
  readonly failed = signal<boolean>(false);

  /** Semanas (columnas) del heatmap. Vacío si no hay datos. */
  readonly weeks = computed<WeekColumn[]>(() => {
    const p = this.payload();
    if (!p) return [];
    return this.buildWeeks(p.contributions);
  });

  /** Etiquetas de mes con su posición de columna. */
  readonly months = computed<MonthLabel[]>(() => this.buildMonthLabels(this.weeks()));

  readonly totalLastYear = computed<number>(() => {
    const t = this.payload()?.total ?? {};
    return t['lastYear'] ?? 0;
  });

  readonly username = computed<string>(() => this.payload()?.username ?? '');

  ngOnInit(): void {
    this.api.getGithubContributions(PORTFOLIO_SLUG).subscribe({
      next: (payload) => {
        this.payload.set(payload);
        this.loading.set(false);
      },
      error: () => {
        // 404 (sin github social) o 502 (API caída) → sección oculta.
        this.failed.set(true);
        this.loading.set(false);
      },
    });
  }

  // ─── Helpers ──────────────────────────────────────────────────────

  /**
   * Convierte el array plano de contribuciones (ordenado por fecha
   * ascendente) en columnas de semanas Sunday-start (matching GitHub).
   * La primera semana puede empezar con nulls (padding) si la primera
   * fecha no es domingo. Idem la última.
   */
  private buildWeeks(contribs: GithubContribution[]): WeekColumn[] {
    if (contribs.length === 0) return [];

    const weeks: WeekColumn[] = [];
    let current: (GithubContribution | null)[] = [];

    // Padding inicial: si la primera fecha NO es domingo, llenamos con
    // nulls hasta el domingo previo.
    const first = new Date(contribs[0].date + 'T00:00:00');
    const firstDow = first.getDay(); // 0 = Sunday
    for (let i = 0; i < firstDow; i++) current.push(null);

    for (const c of contribs) {
      current.push(c);
      if (current.length === 7) {
        weeks.push({ days: current });
        current = [];
      }
    }
    // Padding final: completar la última semana con nulls.
    if (current.length > 0) {
      while (current.length < 7) current.push(null);
      weeks.push({ days: current });
    }
    return weeks;
  }

  /**
   * Detecta cambios de mes recorriendo las semanas — cada vez que
   * aparece un día con `getMonth()` distinto al anterior, marca la
   * columna con la etiqueta abreviada del mes nuevo.
   */
  private buildMonthLabels(weeks: WeekColumn[]): MonthLabel[] {
    const labels: MonthLabel[] = [];
    let lastMonth = -1;
    const monthNames = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
      'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

    weeks.forEach((week, idx) => {
      // Buscamos el primer día real de la semana (skip padding nulls).
      const firstReal = week.days.find((d) => d !== null);
      if (!firstReal) return;
      const month = new Date(firstReal.date + 'T00:00:00').getMonth();
      if (month !== lastMonth) {
        // Skip la primera etiqueta si está demasiado pegada al borde
        // (menos de 3 columnas de la anterior) — evita solapamientos.
        const prev = labels[labels.length - 1];
        if (!prev || idx - prev.weekIndex >= 3) {
          labels.push({ weekIndex: idx, label: monthNames[month] });
        }
        lastMonth = month;
      }
    });
    return labels;
  }

  /** Formatea "1234" → "1,234" para display. */
  formatNumber(n: number): string {
    return n.toLocaleString(this.i18n.lang() === 'es' ? 'es-AR' : 'en-US');
  }

  /** Tooltip por día: "3 contribuciones el 2026-01-01". */
  tooltipFor(day: GithubContribution): string {
    const dict = this.i18n.dict() as unknown as {
      github?: { tooltip?: string; tooltipNone?: string };
    };
    const label = day.count === 0
      ? dict.github?.tooltipNone ?? 'Sin contribuciones el {date}'
      : dict.github?.tooltip ?? '{count} contribuciones el {date}';
    return label.replace('{count}', String(day.count)).replace('{date}', day.date);
  }
}

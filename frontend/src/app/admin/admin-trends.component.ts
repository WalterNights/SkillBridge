import { CommonModule } from '@angular/common';
import { HttpErrorResponse } from '@angular/common/http';
import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { Title } from '@angular/platform-browser';

import {
  AdminService,
  TrendsIgnoreCategoryRow,
  TrendsPortalFunnelRow,
  TrendsResponse,
} from '../services/admin.service';
import { IGNORE_REASON_LABELS, IgnoreReason } from '../models/job-offer.model';

/** Etiquetas legibles de categoría profesional — alinea con
 *  `profession_classifier` del backend. `general` no se muestra porque
 *  la vista lo excluye en la query (evita ensuciar el reporte). */
const CATEGORY_LABELS: Record<string, string> = {
  tech: 'Tecnología',
  design: 'Diseño',
  marketing: 'Marketing',
  sales: 'Ventas',
  finance: 'Finanzas',
  hr: 'Recursos Humanos',
  operations: 'Operaciones',
  agro: 'Agro',
  health: 'Salud',
  education: 'Educación',
  legal: 'Legal',
  admin: 'Administración',
  trades: 'Oficios',
};

/** Portales — replica del map de admin-stats para consistencia visual. */
const PORTAL_LABELS: Record<string, string> = {
  computrabajo: 'Computrabajo',
  linkedin: 'LinkedIn',
  hireline: 'Hireline',
  elempleo: 'Elempleo',
  bumeran: 'Bumeran',
  indeed: 'Indeed',
  magneto: 'Magneto',
  infojobs: 'InfoJobs',
  trabajos_co: 'Trabajos Colombia',
  trabajando: 'Trabajando.com',
  weworkremotely: 'WeWorkRemotely',
  websearch: 'WebSearch (DDG)',
  torre: 'Torre',
  meli: 'MercadoLibre',
  other: 'Otro',
  unknown: 'Sin portal',
};

/**
 * Panel admin: tendencias de comportamiento.
 *
 * Distinto de /admin/stats (que es un snapshot descriptivo). Acá miramos
 * POR QUE el user ignora y COMO convierte cada portal — data que
 * alimenta las decisiones de matching y el ranker personalizado.
 *
 * Comparte los estilos de admin-stats via styleUrls — reusamos las
 * clases .bar-row, .bar-track, .bar-fill, .status-pill, .kpi-card,
 * .analytics-pill. Si en algun momento divergen, refactorizamos a un
 * scss compartido, pero por ahora es la misma estética y no vale la
 * pena scaffolding extra.
 */
@Component({
  selector: 'app-admin-trends',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './admin-trends.component.html',
  styleUrls: ['./admin-stats.component.scss'],
})
export class AdminTrendsComponent implements OnInit {
  private adminService = inject(AdminService);
  private titleService = inject(Title);

  trends = signal<TrendsResponse | null>(null);
  isLoading = signal(true);
  errorMessage = signal('');

  /** Ventana temporal del selector — 7 / 30 / 90 dias. Alinea con
   *  admin-stats (misma UX) y con el backend (que solo acepta esas). */
  windowDays = signal(30);

  /** Max count del breakdown de motivos — para escalar las barras. */
  maxReasonCount = computed(() => {
    const t = this.trends();
    if (!t || t.ignore_breakdown.by_reason.length === 0) return 1;
    return Math.max(...t.ignore_breakdown.by_reason.map((r) => r.count));
  });

  /** Max clicks de portales — escala las barras del funnel. Usamos el
   *  total (clicks) porque es la "base" del funnel; los sub-status son
   *  fracciones de este. */
  maxPortalClicks = computed(() => {
    const t = this.trends();
    if (!t || t.portal_funnel.length === 0) return 1;
    return Math.max(...t.portal_funnel.map((p) => p.clicks));
  });

  /** Motivos agrupados por vertical — pivot de by_category_reason a
   *  {[category]: [{reason, count}]}. Facilita renderizar sub-listas
   *  en el template sin lógica compleja. */
  categoryBreakdown = computed<{ category: string; rows: TrendsIgnoreCategoryRow[] }[]>(() => {
    const t = this.trends();
    if (!t) return [];
    const grouped = new Map<string, TrendsIgnoreCategoryRow[]>();
    for (const row of t.ignore_breakdown.by_category_reason) {
      const list = grouped.get(row.offer__category) ?? [];
      list.push(row);
      grouped.set(row.offer__category, list);
    }
    return Array.from(grouped.entries()).map(([category, rows]) => ({
      category,
      rows: rows.sort((a, b) => b.count - a.count),
    }));
  });

  constructor() {
    this.titleService.setTitle('SkilTak — Admin · Tendencias');
  }

  ngOnInit(): void {
    this.load();
  }

  private load(): void {
    this.isLoading.set(true);
    this.errorMessage.set('');
    this.adminService.getTrends(this.windowDays()).subscribe({
      next: (data) => {
        this.trends.set(data);
        this.isLoading.set(false);
      },
      error: (err: HttpErrorResponse) => {
        this.errorMessage.set(
          err.status === 403
            ? 'No tienes permisos para ver esta sección.'
            : 'Error al cargar las tendencias.',
        );
        this.isLoading.set(false);
      },
    });
  }

  setWindow(days: number): void {
    if (this.windowDays() === days) return;
    this.windowDays.set(days);
    this.load();
  }

  reasonLabel(code: string): string {
    if (!code) return 'Sin motivo';
    return IGNORE_REASON_LABELS[code as IgnoreReason] ?? code;
  }

  categoryLabel(code: string): string {
    return CATEGORY_LABELS[code] ?? code;
  }

  portalLabel(code: string): string {
    return PORTAL_LABELS[code] ?? code;
  }

  /** Fill % de una barra, capeado a [0, 100]. */
  pct(value: number, max: number): number {
    if (max <= 0) return 0;
    return Math.max(0, Math.min(100, (value / max) * 100));
  }

  /** Fracción del funnel usada para pintar segmentos internos ("de los N
   *  clicks del portal, cuántos llegaron a X status"). Se calcula
   *  sobre el total de clicks del portal, no sobre el max global. */
  portalPct(row: TrendsPortalFunnelRow, key: keyof TrendsPortalFunnelRow): number {
    const base = row.clicks;
    if (base <= 0) return 0;
    const value = row[key] as number;
    return Math.max(0, Math.min(100, (value / base) * 100));
  }

  /** Color de conversión: verde >= 8%, amber 3-8%, red < 3%. Umbrales
   *  arbitrarios para el primer pass; ajustar cuando tengamos benchmark
   *  real por vertical. */
  conversionColor(pct: number): 'green' | 'amber' | 'red' {
    if (pct >= 8) return 'green';
    if (pct >= 3) return 'amber';
    return 'red';
  }
}

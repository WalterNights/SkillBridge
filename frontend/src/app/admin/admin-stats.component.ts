import { CommonModule } from '@angular/common';
import { HttpErrorResponse } from '@angular/common/http';
import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { Title } from '@angular/platform-browser';

import { AdminService, AdminStats } from '../services/admin.service';

/** Labels legibles para los códigos ISO de país que devuelve el backend. */
const COUNTRY_LABELS: Record<string, string> = {
  MX: 'México',
  CO: 'Colombia',
  AR: 'Argentina',
  CL: 'Chile',
  PE: 'Perú',
  UY: 'Uruguay',
  PY: 'Paraguay',
  BO: 'Bolivia',
  EC: 'Ecuador',
  VE: 'Venezuela',
  CR: 'Costa Rica',
  PA: 'Panamá',
  DO: 'R. Dominicana',
  GT: 'Guatemala',
  ES: 'España',
  US: 'Estados Unidos',
};

const STATUS_LABELS: Record<string, string> = {
  pending: 'Pendiente',
  applied: 'Aplicada',
  in_review: 'En revisión',
  interview: 'Entrevista',
  offer: 'Oferta recibida',
  rejected: 'Rechazada',
  withdrawn: 'Retirada',
};

const PORTAL_LABELS: Record<string, string> = {
  computrabajo: 'Computrabajo',
  linkedin: 'LinkedIn',
  hireline: 'Hireline',
  elempleo: 'Elempleo',
  bumeran: 'Bumeran',
  indeed: 'Indeed',
  magneto: 'Magneto',
  trabajos_co: 'Trabajos Colombia',
  trabajando: 'Trabajando.com',
  weworkremotely: 'WeWorkRemotely',
  websearch: 'WebSearch (DDG)',
  other: 'Otro',
};

/**
 * Panel admin: estadísticas agregadas de plataforma.
 *
 * Métricas reales desde `/api/dashboard/stats/` — usuarios, ofertas
 * (con breakdown por portal y país), postulaciones por status, tasa
 * de éxito calculada en backend. No hay datos hardcoded.
 */
@Component({
  selector: 'app-admin-stats',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './admin-stats.component.html',
  styleUrls: ['./admin-stats.component.scss'],
})
export class AdminStatsComponent implements OnInit {
  private adminService = inject(AdminService);
  private titleService = inject(Title);

  stats = signal<AdminStats | null>(null);
  isLoading = signal(true);
  errorMessage = signal('');

  /** Max value de offers.by_portal — usado para escalar las barras. */
  maxPortalCount = computed(() => {
    const s = this.stats();
    if (!s || s.offers.by_portal.length === 0) return 1;
    return Math.max(...s.offers.by_portal.map((r) => r.count));
  });

  /** Idem para offers.by_country. */
  maxCountryCount = computed(() => {
    const s = this.stats();
    if (!s || s.offers.by_country.length === 0) return 1;
    return Math.max(...s.offers.by_country.map((r) => r.count));
  });

  /** Idem para applications.by_status. */
  maxStatusCount = computed(() => {
    const s = this.stats();
    if (!s || s.applications.by_status.length === 0) return 1;
    return Math.max(...s.applications.by_status.map((r) => r.count));
  });

  constructor() {
    this.titleService.setTitle('SkilTak — Admin · Estadísticas');
  }

  ngOnInit(): void {
    this.adminService.getStats().subscribe({
      next: (data) => {
        this.stats.set(data);
        this.isLoading.set(false);
      },
      error: (err: HttpErrorResponse) => {
        this.errorMessage.set(
          err.status === 403
            ? 'No tenés permisos para ver esta sección.'
            : 'Error al cargar las estadísticas.',
        );
        this.isLoading.set(false);
      },
    });
  }

  countryLabel(code: string): string {
    return COUNTRY_LABELS[code] ?? code;
  }

  statusLabel(code: string): string {
    return STATUS_LABELS[code] ?? code;
  }

  portalLabel(code: string): string {
    return PORTAL_LABELS[code] ?? code;
  }

  /** Porcentaje de fill para una barra. Capeado a [0, 100]. */
  pct(value: number, max: number): number {
    return Math.max(0, Math.min(100, (value / max) * 100));
  }

  /** Color de la pill por status — alinea con applications.component.scss. */
  statusColor(status: string): string {
    switch (status) {
      case 'applied':
        return 'green';
      case 'in_review':
        return 'amber';
      case 'interview':
        return 'blue';
      case 'offer':
        return 'violet';
      case 'rejected':
      case 'withdrawn':
        return 'grey';
      default:
        return 'pending';
    }
  }
}

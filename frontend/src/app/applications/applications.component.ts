import { CommonModule } from '@angular/common';
import { Component, DestroyRef, computed, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { RouterModule } from '@angular/router';
import { Title } from '@angular/platform-browser';

import {
  ApplicationService,
  ApplicationStatus,
  JobApplicationDto,
  StatusOption,
} from '../services/application.service';
import { portalMeta } from '../shared/portal';

const _RELATIVE_FMT = new Intl.RelativeTimeFormat('es', { numeric: 'auto' });

function _formatRelative(iso: string | null | undefined): string {
  if (!iso) return '';
  const then = new Date(iso).getTime();
  if (Number.isNaN(then)) return '';
  const diffSec = Math.round((then - Date.now()) / 1000);
  const abs = Math.abs(diffSec);
  if (abs < 60) return _RELATIVE_FMT.format(Math.round(diffSec), 'second');
  if (abs < 3600) return _RELATIVE_FMT.format(Math.round(diffSec / 60), 'minute');
  if (abs < 86400) return _RELATIVE_FMT.format(Math.round(diffSec / 3600), 'hour');
  if (abs < 2592000) return _RELATIVE_FMT.format(Math.round(diffSec / 86400), 'day');
  return _RELATIVE_FMT.format(Math.round(diffSec / 2592000), 'month');
}

/** Tabs visibles en el header — agregamos manualmente las que importan,
 * el dropdown del card permite TODOS los status del backend. */
type TabKey = 'all' | 'active' | ApplicationStatus;

interface TabConfig {
  key: TabKey;
  label: string;
}

const TABS: readonly TabConfig[] = [
  { key: 'active', label: 'Activas' },
  { key: 'interview', label: 'Entrevista' },
  { key: 'offer', label: 'Oferta' },
  { key: 'rejected', label: 'Rechazadas' },
  { key: 'all', label: 'Todas' },
];

@Component({
  selector: 'app-applications',
  standalone: true,
  imports: [CommonModule, RouterModule],
  templateUrl: './applications.component.html',
  styleUrl: './applications.component.scss',
})
export class ApplicationsComponent {
  applications = signal<JobApplicationDto[]>([]);
  statusOptions = signal<StatusOption[]>([]);
  isLoading = signal(true);
  errorMessage = signal('');
  activeTab = signal<TabKey>('active');
  /** UI state: id del card abierto (dropdown del cambio de status). */
  openMenuFor = signal<number | null>(null);

  readonly tabs = TABS;

  /** Contador por tab — fetchamos todas las apps una sola vez y
   * filtramos en memoria para evitar N requests. */
  countByTab = computed<Record<TabKey, number>>(() => {
    const all = this.applications();
    return {
      all: all.length,
      active: all.filter((a) =>
        ['applied', 'in_review', 'interview', 'offer'].includes(a.status),
      ).length,
      interview: all.filter((a) => a.status === 'interview').length,
      offer: all.filter((a) => a.status === 'offer').length,
      rejected: all.filter((a) => a.status === 'rejected').length,
      // Resto solo para que el type-check no se queje — no se usan en tabs.
      pending: 0,
      applied: 0,
      in_review: 0,
      withdrawn: 0,
    };
  });

  visibleApplications = computed<JobApplicationDto[]>(() => {
    const all = this.applications();
    const tab = this.activeTab();
    if (tab === 'all') {
      // Filtramos pending — son intents no confirmados, ruido en la vista
      // "Todas". Solo deben renderizarse en el job-detail asking-card.
      return all.filter((a) => a.status !== 'pending');
    }
    if (tab === 'active') {
      return all.filter((a) =>
        ['applied', 'in_review', 'interview', 'offer'].includes(a.status),
      );
    }
    return all.filter((a) => a.status === tab);
  });

  private api = inject(ApplicationService);
  private titleService = inject(Title);
  private destroyRef = inject(DestroyRef);

  constructor() {
    this.titleService.setTitle('SkilTak — Mis postulaciones');
    this.api
      .statusOptions()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (res) => this.statusOptions.set(res.options),
        error: () => {
          /* Fallback: el dropdown queda vacío, el user no puede cambiar
           * status pero el resto de la vista funciona. */
        },
      });
    this.refresh();
  }

  private refresh(): void {
    this.isLoading.set(true);
    this.api
      .list()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (apps) => {
          this.applications.set(apps);
          this.isLoading.set(false);
        },
        error: () => {
          this.errorMessage.set('No pudimos cargar tus postulaciones.');
          this.isLoading.set(false);
        },
      });
  }

  setTab(tab: TabKey): void {
    this.activeTab.set(tab);
    this.openMenuFor.set(null);
  }

  toggleMenu(applicationId: number, event: Event): void {
    event.stopPropagation();
    this.openMenuFor.update((current) => (current === applicationId ? null : applicationId));
  }

  /** Optimistic update: cambiamos el status localmente y rollback on error. */
  onStatusChange(application: JobApplicationDto, newStatus: ApplicationStatus): void {
    this.openMenuFor.set(null);
    if (application.status === newStatus) return;
    const previousStatus = application.status;
    this.applications.update((list) =>
      list.map((a) => (a.id === application.id ? { ...a, status: newStatus } : a)),
    );
    this.api.updateStatus(application.id, newStatus).subscribe({
      next: (updated) => {
        // Reemplazamos con el dto fresco (incluye status_changed_at actualizado).
        this.applications.update((list) =>
          list.map((a) => (a.id === updated.id ? updated : a)),
        );
      },
      error: () => {
        // Rollback
        this.applications.update((list) =>
          list.map((a) =>
            a.id === application.id ? { ...a, status: previousStatus } : a,
          ),
        );
      },
    });
  }

  portalMetaFor(app: JobApplicationDto) {
    return portalMeta(app.offer);
  }

  /** Best-effort "última actividad" — status_changed_at, fallback a applied_at. */
  lastActivityRelative(app: JobApplicationDto): string {
    return _formatRelative(app.status_changed_at ?? app.applied_at);
  }

  /** Label en español del status, derivado del catálogo del backend. */
  labelForStatus(status: ApplicationStatus): string {
    const opt = this.statusOptions().find((o) => o.value === status);
    return opt?.label ?? status;
  }

  /** Cierra el dropdown si se clickea fuera del card. */
  closeMenu(): void {
    this.openMenuFor.set(null);
  }
}

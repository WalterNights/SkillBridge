import { CommonModule } from '@angular/common';
import { Component, DestroyRef, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { RouterModule } from '@angular/router';
import { Title } from '@angular/platform-browser';

import {
  ApplicationService,
  JobApplicationDto,
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

/**
 * "Mis postulaciones" — lista de JobApplication del user, filtrada por
 * status=applied (las pending son ofertas que el user clickeó pero no
 * confirmó, no las queremos mostrar acá como si las hubiera aplicado).
 *
 * Renderiza dentro del AppShell, así que no monta header/sidebar propio.
 */
@Component({
  selector: 'app-applications',
  standalone: true,
  imports: [CommonModule, RouterModule],
  templateUrl: './applications.component.html',
  styleUrl: './applications.component.scss',
})
export class ApplicationsComponent {
  applications = signal<JobApplicationDto[]>([]);
  isLoading = signal(true);
  errorMessage = signal('');

  private api = inject(ApplicationService);
  private titleService = inject(Title);
  private destroyRef = inject(DestroyRef);

  constructor() {
    this.titleService.setTitle('SkilTak — Mis postulaciones');
    this.api
      .list()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (apps) => {
          // Solo `applied`. Las `pending` son ruido — el user nunca
          // confirmó, no debería verlas como "ya aplicaste a esto".
          this.applications.set(apps.filter((a) => a.status === 'applied'));
          this.isLoading.set(false);
        },
        error: () => {
          this.errorMessage.set('No pudimos cargar tus postulaciones.');
          this.isLoading.set(false);
        },
      });
  }

  portalMetaFor(app: JobApplicationDto) {
    return portalMeta(app.offer);
  }

  appliedRelative(app: JobApplicationDto): string {
    return _formatRelative(app.applied_at);
  }
}

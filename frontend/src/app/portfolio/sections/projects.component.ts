import { Component, computed, inject, signal } from '@angular/core';

import { PortfolioI18nService } from '../i18n/portfolio-i18n.service';
import { PfSectionHeaderComponent } from './section-header.component';

/** Shape esperado de cada item en `projects.items` (backend o bundled JSON). */
export interface PortfolioProject {
  id: string;
  name: string;
  kind: 'personal' | 'enterprise';
  status: 'live' | 'private' | 'wip';
  description: string;
  stack: string[];
  href?: string;
  repo?: string;
}

type FilterKind = 'all' | PortfolioProject['kind'];

@Component({
  selector: 'app-projects-section',
  standalone: true,
  imports: [PfSectionHeaderComponent],
  templateUrl: './projects.component.html',
  styleUrl: './projects.component.scss',
})
export class ProjectsSectionComponent {
  readonly i18n = inject(PortfolioI18nService);

  readonly filter = signal<FilterKind>('all');
  readonly filters: readonly FilterKind[] = ['all', 'personal', 'enterprise'];

  /** Lista de proyectos leída del diccionario activo (i18n). Fallback
   *  a array vacío si el JSON no tiene la sección (protección contra
   *  seed incompleto o traducción a medias). */
  readonly items = computed<PortfolioProject[]>(() => {
    const arr = this.i18n.raw<PortfolioProject[]>('projects.items');
    return Array.isArray(arr) ? arr : [];
  });

  readonly filtered = computed<PortfolioProject[]>(() => {
    const f = this.filter();
    if (f === 'all') return this.items();
    return this.items().filter((p) => p.kind === f);
  });

  setFilter(f: FilterKind): void {
    this.filter.set(f);
  }

  labelOf(key: string): string {
    return this.i18n.t(`projects.labels.${key}`);
  }

  filterLabel(f: FilterKind): string {
    return this.i18n.t(`projects.filters.${f}`);
  }

  /** Devuelve la URL del cover si el backend subió una imagen para
   *  este project_id; undefined si no hay imagen (activa el placeholder). */
  coverFor(project: PortfolioProject): string | undefined {
    return this.i18n.imageFor(project.id)?.url;
  }

  coverAltFor(project: PortfolioProject): string {
    return this.i18n.imageFor(project.id)?.alt || project.name;
  }
}

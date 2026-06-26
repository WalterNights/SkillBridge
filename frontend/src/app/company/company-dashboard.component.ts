import { CommonModule } from '@angular/common';
import { HttpErrorResponse } from '@angular/common/http';
import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Title } from '@angular/platform-browser';

import {
  CompanyService,
  ProfileSearchResult,
} from '../services/company.service';

/** Estado local del form de criterios. Lo persistimos en sessionStorage
 *  para que el F5 no haga perder lo que el admin tipeó. */
interface CriteriaForm {
  skills_required: string; // CSV; el split se hace al submit
  target_title: string;
  country: string;
  min_match: number;
}

const CRITERIA_STORAGE_KEY = 'company_search_criteria';

const DEFAULT_CRITERIA: CriteriaForm = {
  skills_required: '',
  target_title: '',
  country: '',
  min_match: 50,
};

/**
 * Feed de profesionales del lado empresa.
 *
 * El admin define criterios (skills, título objetivo, país, match
 * mínimo) y dispara la búsqueda. El backend reusa `JobMatchingService`
 * invertido y devuelve cards ordenadas por match%.
 *
 * Privacy guarantees del backend que asumimos acá:
 *   - Solo profesionales con `visible_to_companies=True` aparecen.
 *   - Las cards NO traen email/telefono — solo match + skills + city.
 *   - Para contactar al profesional vamos a un flow de "marcar interés"
 *     en una fase siguiente.
 */
@Component({
  selector: 'app-company-dashboard',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './company-dashboard.component.html',
  styleUrls: ['./company-dashboard.component.scss'],
})
export class CompanyDashboardComponent implements OnInit {
  private companyService = inject(CompanyService);

  criteria = signal<CriteriaForm>({ ...DEFAULT_CRITERIA });
  results = signal<ProfileSearchResult[]>([]);
  total = signal(0);
  hasSearched = signal(false);
  isLoading = signal(false);
  errorMessage = signal('');

  /** True si el form tiene al menos uno de skills_required o target_title.
   *  Botón Buscar deshabilitado cuando es false. */
  canSearch = computed(() => {
    const c = this.criteria();
    return c.skills_required.trim().length > 0 || c.target_title.trim().length > 0;
  });

  constructor(title: Title) {
    title.setTitle('SkilTak — Buscar profesionales');
  }

  ngOnInit(): void {
    // Restaurar criterios previos si existen — UX mejor que blanco
    // total al cargar.
    try {
      const raw = sessionStorage.getItem(CRITERIA_STORAGE_KEY);
      if (raw) {
        const stored = JSON.parse(raw);
        this.criteria.set({ ...DEFAULT_CRITERIA, ...stored });
        // Si había búsqueda válida, ejecutarla automáticamente para
        // que el admin no tenga que tipear de nuevo.
        if (this.canSearch()) this.search();
      }
    } catch {
      /* swallow — si parseo falla, partimos limpio */
    }
  }

  updateCriteria<K extends keyof CriteriaForm>(key: K, value: CriteriaForm[K]): void {
    const next = { ...this.criteria(), [key]: value };
    this.criteria.set(next);
  }

  search(): void {
    if (!this.canSearch()) return;

    this.isLoading.set(true);
    this.errorMessage.set('');

    const c = this.criteria();
    const skills = c.skills_required
      .split(',')
      .map((s) => s.trim())
      .filter((s) => s.length > 0);

    // Persistir para próxima visita.
    try {
      sessionStorage.setItem(CRITERIA_STORAGE_KEY, JSON.stringify(c));
    } catch {
      /* swallow */
    }

    this.companyService
      .searchProfiles({
        skills_required: skills,
        target_title: c.target_title.trim(),
        country: c.country.trim() || undefined,
        min_match: c.min_match,
      })
      .subscribe({
        next: (res) => {
          this.results.set(res.results);
          this.total.set(res.total);
          this.hasSearched.set(true);
          this.isLoading.set(false);
        },
        error: (err: HttpErrorResponse) => {
          this.isLoading.set(false);
          this.hasSearched.set(true);
          if (err.status === 403) {
            this.errorMessage.set(
              'Tu cuenta no es de tipo empresa. Si esto es un error, contacta soporte.',
            );
          } else {
            this.errorMessage.set('No pudimos completar la búsqueda. Intenta de nuevo.');
          }
        },
      });
  }

  clear(): void {
    this.criteria.set({ ...DEFAULT_CRITERIA });
    this.results.set([]);
    this.total.set(0);
    this.hasSearched.set(false);
    this.errorMessage.set('');
    sessionStorage.removeItem(CRITERIA_STORAGE_KEY);
  }

  initials(p: ProfileSearchResult): string {
    return ((p.first_name || '?').charAt(0) + (p.last_name || '').charAt(0)).toUpperCase();
  }

  matchColor(pct: number): 'high' | 'mid' | 'low' {
    if (pct >= 80) return 'high';
    if (pct >= 60) return 'mid';
    return 'low';
  }

  trackProfile(_index: number, p: ProfileSearchResult): number {
    return p.profile_id;
  }
}

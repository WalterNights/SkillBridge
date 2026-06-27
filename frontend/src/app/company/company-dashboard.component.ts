import { CommonModule } from '@angular/common';
import { HttpErrorResponse } from '@angular/common/http';
import {
  Component,
  DestroyRef,
  OnInit,
  computed,
  effect,
  inject,
  signal,
} from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormsModule } from '@angular/forms';
import { Title } from '@angular/platform-browser';
import { RouterLink } from '@angular/router';
import { Subject, debounceTime } from 'rxjs';

import {
  CompanyService,
  ProfileCategory,
  ProfileSearchResult,
} from '../services/company.service';

/** Form state de los filtros. Todos opcionales — se refinan en vivo
 *  sobre la lista base. Persistido en sessionStorage para que F5 no
 *  pierda lo que el admin estaba mirando. */
interface FiltersForm {
  skills_required: string;       // CSV
  target_title: string;
  country: string;
  profession_category: string;   // value del dropdown (vacío = todas)
  min_match: number;             // solo aplica cuando hay match%
}

const FILTERS_STORAGE_KEY = 'company_filters_v2';

const DEFAULT_FILTERS: FiltersForm = {
  skills_required: '',
  target_title: '',
  country: '',
  profession_category: '',
  min_match: 50,
};

/**
 * Bolsa de profesionales (vista empresa).
 *
 * Modelo de UX desde 2026-06-27: LISTA-FIRST.
 * Al entrar, mostramos TODOS los profiles visibles (cards básicas, sin
 * porcentaje de match). Los filtros — dropdown de categoría profesional
 * + skills + título objetivo + país — refinan la lista en vivo con
 * debounce 400ms.
 *
 * Cuando el admin agrega `skills_required` o `target_title`, el backend
 * activa el modo BÚSQUEDA y devuelve cards CON match% ordenadas. Si
 * vuelve a vaciar esos campos, volvemos a modo NAVEGAR.
 *
 * Privacy: como antes, solo perfiles `visible_to_companies=True` y sin
 * PII de contacto en las cards.
 */
@Component({
  selector: 'app-company-dashboard',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink],
  templateUrl: './company-dashboard.component.html',
  styleUrls: ['./company-dashboard.component.scss'],
})
export class CompanyDashboardComponent implements OnInit {
  private companyService = inject(CompanyService);
  private destroyRef = inject(DestroyRef);

  filters = signal<FiltersForm>({ ...DEFAULT_FILTERS });
  results = signal<ProfileSearchResult[]>([]);
  total = signal(0);
  categories = signal<ProfileCategory[]>([]);
  /** Modo del último request: true = NAVEGAR (sin match%), false = BUSCAR. */
  browseMode = signal(true);
  isLoading = signal(false);
  errorMessage = signal('');

  /** Debounce stream: el input cambia, espera 400ms, dispara refresh.
   *  Evita pegarle al backend en cada tecla. */
  private refreshTrigger$ = new Subject<void>();

  /** True si hay al menos un filtro distinto al default — habilita el
   *  botón "Limpiar filtros". */
  hasActiveFilters = computed(() => {
    const f = this.filters();
    return (
      f.skills_required.trim().length > 0 ||
      f.target_title.trim().length > 0 ||
      f.country.trim().length > 0 ||
      f.profession_category.length > 0
    );
  });

  /** True si los filtros activan match%: el backend pasa a modo BÚSQUEDA. */
  hasMatchCriteria = computed(() => {
    const f = this.filters();
    return f.skills_required.trim().length > 0 || f.target_title.trim().length > 0;
  });

  constructor(title: Title) {
    title.setTitle('SkilTak — Buscar profesionales');

    // Wiring del debounce — cada cambio en filtros pasa por acá.
    this.refreshTrigger$
      .pipe(debounceTime(400), takeUntilDestroyed(this.destroyRef))
      .subscribe(() => this.fetch());

    // Persistir filtros automáticamente al cambiar.
    effect(() => {
      const current = this.filters();
      try {
        sessionStorage.setItem(FILTERS_STORAGE_KEY, JSON.stringify(current));
      } catch {
        /* swallow */
      }
    });
  }

  ngOnInit(): void {
    // Restaurar filtros previos si existen, sino arrancar limpio.
    try {
      const raw = sessionStorage.getItem(FILTERS_STORAGE_KEY);
      if (raw) {
        const stored = JSON.parse(raw);
        this.filters.set({ ...DEFAULT_FILTERS, ...stored });
      }
    } catch {
      /* swallow */
    }

    // Cargar categorías + lista inicial en paralelo.
    this.loadCategories();
    this.fetch();
  }

  private loadCategories(): void {
    this.companyService.getProfileCategories().subscribe({
      next: (res) => this.categories.set(res.categories),
      error: () => {
        /* Soft-fail: el dropdown queda vacío pero el resto del feed
         * sigue andando. */
      },
    });
  }

  /** Update parcial de un filtro. Dispara el debounce trigger. */
  updateFilter<K extends keyof FiltersForm>(key: K, value: FiltersForm[K]): void {
    this.filters.update((current) => ({ ...current, [key]: value }));
    this.refreshTrigger$.next();
  }

  clear(): void {
    this.filters.set({ ...DEFAULT_FILTERS });
    this.refreshTrigger$.next();
  }

  /** Ejecuta el request al backend con los filtros actuales. */
  private fetch(): void {
    this.isLoading.set(true);
    this.errorMessage.set('');

    const f = this.filters();
    const skills = f.skills_required
      .split(',')
      .map((s) => s.trim())
      .filter((s) => s.length > 0);

    this.companyService
      .searchProfiles({
        skills_required: skills.length ? skills : undefined,
        target_title: f.target_title.trim() || undefined,
        country: f.country.trim() || undefined,
        profession_category: f.profession_category || undefined,
        // min_match solo tiene sentido en modo BÚSQUEDA — si pasamos
        // sin criterios, el backend lo ignora.
        min_match: this.hasMatchCriteria() ? f.min_match : undefined,
      })
      .subscribe({
        next: (res) => {
          this.results.set(res.results);
          this.total.set(res.total);
          this.browseMode.set(res.browse_mode ?? res.criteria_empty);
          this.isLoading.set(false);
        },
        error: (err: HttpErrorResponse) => {
          this.isLoading.set(false);
          if (err.status === 403) {
            this.errorMessage.set(
              'Tu cuenta no es de tipo empresa. Si esto es un error, contacta soporte.',
            );
          } else {
            this.errorMessage.set('No pudimos cargar la lista. Intenta de nuevo.');
          }
        },
      });
  }

  initials(p: ProfileSearchResult): string {
    return ((p.first_name || '?').charAt(0) + (p.last_name || '').charAt(0)).toUpperCase();
  }

  matchColor(pct: number | null): 'high' | 'mid' | 'low' {
    if (pct === null) return 'low';
    if (pct >= 80) return 'high';
    if (pct >= 60) return 'mid';
    return 'low';
  }

  trackProfile(_index: number, p: ProfileSearchResult): number {
    return p.profile_id;
  }
}

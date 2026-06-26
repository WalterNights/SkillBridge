import { Component, computed, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Title } from '@angular/platform-browser';
import { HttpErrorResponse } from '@angular/common/http';
import { JobOffer } from '../models/job-offer.model';
import {
  FilterOptionsResponse,
  JobFilters,
  JobService,
  ScrapeResponse,
} from '../services/job.service';
import { ScrapeProgressService } from '../services/scrape-progress.service';
import { ToastService } from '../services/toast.service';
import { Router, RouterModule } from '@angular/router';
import { HTMLChangesComponent } from '../shared/html-changes/html-changes';
import { MATCH_THRESHOLDS } from '../constants/match-thresholds';
import { portalMeta } from '../shared/portal';

/** Etiqueta legible de un código ISO 3166-1 alpha-2 para el dropdown.
 * Cubrimos los países activos en LATAM + ES/US. Si falta uno, se muestra
 * el código tal cual (fallback aceptable). */
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

/**
 * Results component for displaying job offers with filtering
 */
@Component({
  selector: 'app-results',
  imports: [CommonModule, RouterModule],
  standalone: true,
  templateUrl: './results.component.html',
  styleUrls: ['./results.component.scss'],
})
export class ResultsComponent {
  offers: JobOffer[] = [];
  hoverState: { [offerId: number]: boolean } = {};
  selectedFilter: 'all' | 'good' | 'regular' | 'bad' = 'all';

  /** Estado de paginación. El backend pagina con DRF (PAGE_SIZE=20).
   * `offers` acumula página a página — clicker "Cargar más" appendea,
   * cambiar filtros resetea a página 1. */
  currentPage = signal<number>(1);
  totalCount = signal<number>(0);
  hasMore = signal<boolean>(false);
  isLoadingMore = signal<boolean>(false);

  /** Catálogo de filtros disponibles (poblado al mount via filter-options
   * endpoint). Mientras está vacío, los dropdowns no se renderizan. */
  filterOptions = signal<FilterOptionsResponse | null>(null);
  /** Selección actual de filtros — disparan recarga al cambiar. */
  selectedCountries = signal<Set<string>>(new Set());
  selectedModalities = signal<Set<string>>(new Set());
  /** UI: panel de filtros abierto/cerrado. */
  filtersOpen = signal<boolean>(false);

  /** True si hay al menos un filtro activo — muestra el botón "Limpiar". */
  hasActiveFilters = computed(
    () => this.selectedCountries().size > 0 || this.selectedModalities().size > 0,
  );

  /** Orden actual del feed por % match.
   *   'desc' (default) → mejor match primero — lo que el user quiere ver.
   *   'asc'            → peor match primero — útil para revisar al final
   *                      qué ofertas no le calzan tanto.
   * Aplicado client-side sobre los resultados ya cargados (no re-fetch). */
  sortOrder = signal<'desc' | 'asc'>('desc');

  /** True si el usuario disparó un scrape en esta sesión. Una de las dos
   * señales que usamos para decidir qué empty-state mostrar. */
  private didScrape = signal<boolean>(false);

  /** True si la DB ya tiene ofertas (independientemente del match% del
   * usuario actual). Lo derivamos del response de filter-options: si
   * hay países o modalidades con count > 0, hay ofertas en el sistema.
   * Sin esto, un user que entra a un feed vacío por umbral 60% pero
   * con DB poblada veía "Pedí tu primera búsqueda", lo cual es falso. */
  hasOffersInDb = computed(() => {
    const opts = this.filterOptions();
    if (!opts) return false;
    return opts.countries.length > 0 || opts.modalities.length > 0;
  });

  /** True = el feed vacío amerita el mensaje "ajustá tu perfil" (ya
   * hay ofertas pero ninguna te calza). False = mensaje genérico
   * "pedí tu primera búsqueda". */
  hasSearched = computed(() => this.didScrape() || this.hasOffersInDb());

  /** Resumen legible del último scrape para el empty-state — formato
   * "N portales (M ofertas revisadas)". Texto neutral si no hay stats
   * en esta sesión (ej. ofertas que ya estaban en DB). */
  private lastScrapeSummary = signal<string>('todos los portales disponibles');
  lastScrapeStats = computed(() => this.lastScrapeSummary());

  /** Label legible para un código ISO. */
  countryLabel(code: string): string {
    return COUNTRY_LABELS[code] || code;
  }

  private readonly MATCH_THRESHOLD = MATCH_THRESHOLDS;

  constructor(
    private router: Router,
    private jobService: JobService,
    private scrapeProgress: ScrapeProgressService,
    private toast: ToastService,
    private titleService: Title,
    private changes: HTMLChangesComponent,
  ) {
    this.titleService.setTitle('SkilTak - Resultados de Búsqueda');
  }

  ngOnInit(): void {
    this.loadOffers();
    this.loadFilterOptions();
  }

  private loadFilterOptions(): void {
    this.jobService.getFilterOptions().subscribe({
      next: (options) => this.filterOptions.set(options),
      error: () => {
        /* Soft-fail: el dashboard funciona sin filtros, simplemente
         * el panel no se muestra. */
      },
    });
  }

  toggleFiltersPanel(): void {
    this.filtersOpen.update((open) => !open);
  }

  toggleCountry(code: string): void {
    this.selectedCountries.update((set) => {
      const next = new Set(set);
      next.has(code) ? next.delete(code) : next.add(code);
      return next;
    });
    this.loadOffers();
  }

  toggleModality(value: string): void {
    this.selectedModalities.update((set) => {
      const next = new Set(set);
      next.has(value) ? next.delete(value) : next.add(value);
      return next;
    });
    this.loadOffers();
  }

  clearFilters(): void {
    this.selectedCountries.set(new Set());
    this.selectedModalities.set(new Set());
    this.loadOffers();
  }

  isCountrySelected(code: string): boolean {
    return this.selectedCountries().has(code);
  }

  isModalitySelected(value: string): boolean {
    return this.selectedModalities().has(value);
  }

  /** Construye el dict de filtros que va al backend — fuente única para
   * loadOffers y loadMore, así no se desincronizan. Incluye el ordering
   * por % match para que el backend ordene la lista completa antes de
   * paginar (sino el sort solo aplica a la página visible).
   *
   * No mandamos `minMatch` — el backend aplica el default (60%) que
   * honra el slogan "cero ruido". Si el feed queda vacío para un perfil
   * que el scraping no cubre, mostramos un empty-state con CTA en vez
   * de inundar con ofertas mediocres.
   */
  private currentFilters(): JobFilters {
    return {
      countries: Array.from(this.selectedCountries()),
      modalities: Array.from(this.selectedModalities()),
      ordering: this.sortOrder() === 'desc' ? 'match_desc' : 'match_asc',
    };
  }

  /** Reset + fetch primera página. Disparado al mount, al cambiar filtros
   * o al regenerar tras un scrape — siempre arranca de cero. */
  private loadOffers(): void {
    this.currentPage.set(1);
    this.jobService.getJobs(this.currentFilters(), 1).subscribe({
      next: (response) => {
        this.offers = response.results;
        this.totalCount.set(response.count);
        this.hasMore.set(response.next !== null);
      },
      error: (err: HttpErrorResponse) => {
        console.error('Failed to load job offers:', err);
        this.offers = [];
        this.totalCount.set(0);
        this.hasMore.set(false);
      },
    });
  }

  /** Append de la siguiente página al final de `offers`. No-op si ya
   * estamos cargando o si no hay más páginas. Optimistic: incrementa
   * la página antes de la request; si falla, rollback. */
  loadMore(): void {
    if (this.isLoadingMore() || !this.hasMore()) return;
    const nextPage = this.currentPage() + 1;
    this.isLoadingMore.set(true);
    this.jobService.getJobs(this.currentFilters(), nextPage).subscribe({
      next: (response) => {
        // Append manteniendo el orden. Como el backend ordena por
        // -created_at, las nuevas páginas son MÁS VIEJAS — concatenar
        // al final es la semántica correcta.
        this.offers = [...this.offers, ...response.results];
        this.currentPage.set(nextPage);
        this.totalCount.set(response.count);
        this.hasMore.set(response.next !== null);
        this.isLoadingMore.set(false);
      },
      error: () => {
        this.isLoadingMore.set(false);
        this.toast.error('No pudimos cargar más ofertas. Intentá de nuevo.');
      },
    });
  }

  /**
   * Filtered offers — el chip (Todas/Excelente/Bueno/Regular) achica la
   * página visible. El ORDEN viene del backend (server-side por match),
   * no lo tocamos acá; sino el sort solo aplicaría a la página actual y
   * no a las 100+ restantes del "Cargar más".
   */
  get filteredOffer(): JobOffer[] {
    switch (this.selectedFilter) {
      case 'good':
        return this.offers.filter(
          (offer) => offer.match_percentage === this.MATCH_THRESHOLD.EXCELLENT,
        );
      case 'regular':
        return this.offers.filter(
          (offer) =>
            offer.match_percentage >= this.MATCH_THRESHOLD.GOOD_MIN &&
            offer.match_percentage <= this.MATCH_THRESHOLD.GOOD_MAX,
        );
      case 'bad':
        return this.offers.filter(
          (offer) =>
            offer.match_percentage >= this.MATCH_THRESHOLD.REGULAR_MIN &&
            offer.match_percentage <= this.MATCH_THRESHOLD.REGULAR_MAX,
        );
      default:
        return this.offers;
    }
  }

  setFilter(filter: 'all' | 'good' | 'regular' | 'bad') {
    this.selectedFilter = filter;
  }

  /** Toggle entre orden asc/desc por % match. Refetcha la página 1 porque
   * el orden ahora vive en el backend — sin esto, mezclaríamos paginas
   * con criterios distintos. */
  toggleSortOrder(): void {
    this.sortOrder.update((order) => (order === 'desc' ? 'asc' : 'desc'));
    this.loadOffers();
  }

  /**
   * Navigates to job detail page
   * @param job - Job offer to view
   */
  goToDetail(job: JobOffer): void {
    this.jobService.setSelectedJob(job);
    this.router.navigate(['/jobs', job.id]);
  }

  /**
   * Sets hover state for a job card
   * @param state - Hover state
   * @param offerId - ID of the job offer
   */
  onHover(state: boolean, offerId: number): void {
    this.hoverState[offerId] = state;
  }

  /**
   * Checks if a job card is hovered
   * @param offerId - ID of the job offer
   * @returns True if hovered
   */
  isHovered(offerId: number): boolean {
    return this.hoverState[offerId] || false;
  }

  /**
   * Gets color for match percentage
   * @param match - Match percentage
   * @returns Color string
   */
  setColor(match: number): string {
    return this.changes.getColor(match);
  }

  /**
   * Gets gradient for match percentage
   * @param match - Match percentage
   * @param hovered - Hover state
   * @returns Gradient string
   */
  setGradient(match: number, hovered: boolean): string {
    return this.changes.getGradient(match, hovered);
  }

  /**
   * Gets width based on hover state
   * @param hovered - Hover state
   * @returns Width string
   */
  setWidth(hovered: boolean): string {
    return this.changes.getWidth(hovered);
  }

  /** Portal de origen del offer (LinkedIn, Elempleo, …) para el avatar. */
  portalMeta(offer: JobOffer) {
    return portalMeta(offer);
  }

  /** Tier de match — usado como atributo CSS para colorear borde + pill. */
  matchTier(percentage: number): 'excellent' | 'good' | 'regular' {
    if (percentage === this.MATCH_THRESHOLD.EXCELLENT) return 'excellent';
    if (percentage >= this.MATCH_THRESHOLD.GOOD_MIN) return 'good';
    return 'regular';
  }

  /** Skills que matchearon contra el perfil. */
  skillsMatched(offer: JobOffer): number {
    return offer.matched_skills?.length ?? 0;
  }

  /** Total = matched + missing. Si no hay data del backend (oferta sin
   * keywords parseadas), devolvemos 1 para que la barra no se rompa. */
  skillsTotal(offer: JobOffer): number {
    const m = offer.matched_skills?.length ?? 0;
    const x = offer.missing_skills?.length ?? 0;
    return m + x || 1;
  }

  /** Porcentaje de fill para la barra de skills. Capeado a [0, 100]. */
  skillsFillPct(offer: JobOffer): number {
    return Math.max(0, Math.min(100, (this.skillsMatched(offer) / this.skillsTotal(offer)) * 100));
  }

  /** trackBy para el *ngFor del feed — evita rebuild completo al filtrar. */
  trackOffer(_index: number, offer: JobOffer): number {
    return offer.id;
  }

  /** Oculta la oferta del feed (optimista) y persiste en backend.
   * Si falla, rollback + toast. El `$event.stopPropagation()` lo hace el template. */
  ignoreOffer(offer: JobOffer): void {
    const original = this.offers;
    this.offers = original.filter((o) => o.id !== offer.id);
    this.totalCount.update((n) => Math.max(0, n - 1));
    this.jobService.ignoreOffer(offer.id).subscribe({
      next: () => this.toast.success('Oferta ignorada — no la verás más en el feed.'),
      error: () => {
        this.offers = original;
        this.totalCount.update((n) => n + 1);
        this.toast.error('No pudimos ignorar la oferta. Intentá de nuevo.');
      },
    });
  }

  /**
   * Dispara un scrape nuevo y refresca la lista visible.
   *
   * El endpoint `/scrape/` devuelve SOLO las ofertas nuevas que pasaron
   * el filtro de match para el usuario — puede ser un array chico (o
   * vacío) aunque la DB tenga más. Por eso después del scrape pedimos
   * el listado completo via `getJobs()` para reflejar el estado real.
   */
  obtainOffers(): void {
    // El scrape ahora tiene su propio notifier persistente bottom-right
    // con barra de progreso y ETA. Los toasts efímeros del top-right ya
    // no son apropiados para una operación que tarda 15-30s.
    this.scrapeProgress.start();
    this.jobService.getScrapedOffers().subscribe({
      next: (response: ScrapeResponse) => {
        const newOffers = response.offers ?? [];
        const stats = response.scrape_stats ?? {};
        this.scrapeProgress.complete({
          newOffersCount: newOffers.length,
          stats,
        });
        // Marcamos "ya buscó" para que el empty-state muestre el mensaje
        // honesto ("ninguna alcanzó 60%") en vez del genérico inicial.
        this.didScrape.set(true);
        const totalFound = Object.values(stats).reduce(
          (acc, s) => acc + (s?.found ?? 0),
          0,
        );
        const portalsCount = Object.keys(stats).length;
        this.lastScrapeSummary.set(
          `${portalsCount} ${portalsCount === 1 ? 'portal' : 'portales'} (${totalFound} ofertas revisadas)`,
        );
        this.loadOffers();
      },
      error: (err: HttpErrorResponse) => {
        console.error('Error fetching job offers:', err);
        let message: string;
        if (err.status === 400 && err.error?.error) {
          message = err.error.error;
        } else if (err.status === 400) {
          message = 'Necesitamos tu título profesional y ciudad antes de buscar ofertas.';
        } else if (err.status === 404) {
          message = 'No se encontró tu perfil. Creá uno primero.';
        } else {
          message = 'No pudimos obtener ofertas. Intentá de nuevo en unos segundos.';
        }
        this.scrapeProgress.fail(message);
      },
    });
  }

  /** CTA del empty-state "ninguna oferta matchea al 60%" — navegar al
   * editor de perfil para refinar título / skills y mejorar el matching. */
  goToProfile(): void {
    this.router.navigate(['/profile']);
  }
}

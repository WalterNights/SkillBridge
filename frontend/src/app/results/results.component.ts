import { Component, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Title } from '@angular/platform-browser';
import { HttpErrorResponse } from '@angular/common/http';
import { JobOffer } from '../models/job-offer.model';
import { JobService, ScrapeResponse } from '../services/job.service';
import { ApplicationService } from '../services/application.service';
import { ToastService } from '../services/toast.service';
import { Router, RouterModule } from '@angular/router';
import { HTMLChangesComponent } from '../shared/html-changes/html-changes';
import { MATCH_THRESHOLDS } from '../constants/match-thresholds';
import { portalMeta } from '../shared/portal';

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

  /** Set de offer_ids ya aplicados por el user — usado para mostrar el
   * badge "Aplicado" en las cards. Se llena al loguear / al volver al
   * feed. Lo mantenemos como Signal<Set> para lookup O(1) en el ngFor. */
  appliedOfferIds = signal<Set<number>>(new Set());

  private readonly MATCH_THRESHOLD = MATCH_THRESHOLDS;

  constructor(
    private router: Router,
    private jobService: JobService,
    private applicationService: ApplicationService,
    private toast: ToastService,
    private titleService: Title,
    private changes: HTMLChangesComponent,
  ) {
    this.titleService.setTitle('SkilTak - Resultados de Búsqueda');
  }

  ngOnInit(): void {
    this.loadOffers();
    this.loadAppliedIds();
  }

  private loadAppliedIds(): void {
    this.applicationService.appliedOfferIds().subscribe({
      next: (res) => this.appliedOfferIds.set(new Set(res.applied_offer_ids)),
      error: () => {
        /* Soft-fail: feed se renderiza sin badges. */
      },
    });
  }

  /** Usado por el template para condicionar el badge "Aplicado". */
  isApplied(offer: JobOffer): boolean {
    return this.appliedOfferIds().has(offer.id);
  }

  private loadOffers(): void {
    this.jobService.getJobs().subscribe({
      next: (data) => {
        this.offers = data;
      },
      error: (err: HttpErrorResponse) => {
        console.error('Failed to load job offers:', err);
        this.offers = [];
      },
    });
  }

  /**
   * Returns filtered offers based on selected filter
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

  /**
   * Dispara un scrape nuevo y refresca la lista visible.
   *
   * El endpoint `/scrape/` devuelve SOLO las ofertas nuevas que pasaron
   * el filtro de match para el usuario — puede ser un array chico (o
   * vacío) aunque la DB tenga más. Por eso después del scrape pedimos
   * el listado completo via `getJobs()` para reflejar el estado real.
   */
  obtainOffers(): void {
    this.toast.info('Buscando ofertas en los portales...', 'Cargando');
    this.jobService.getScrapedOffers().subscribe({
      next: (response: ScrapeResponse) => {
        const newOffers = response.offers ?? [];
        const stats = response.scrape_stats ?? {};
        const breakdown = Object.entries(stats)
          .map(([portal, s]) => {
            if (s.error) return `${portal}: error`;
            if (s.found === 0) return `${portal}: 0`;
            return `${portal}: ${s.found} (nuevas: ${s.saved_new})`;
          })
          .join(' · ');

        if (newOffers.length > 0) {
          this.toast.success(
            `Se agregaron ${newOffers.length} ofertas nuevas. ${breakdown}`,
            '¡Listo!',
          );
        } else {
          this.toast.info(
            `No hay ofertas nuevas. ${breakdown}`,
            'Sin novedades',
          );
        }
        this.loadOffers();
      },
      error: (err: HttpErrorResponse) => {
        console.error('Error fetching job offers:', err);
        if (err.status === 400 && err.error?.error) {
          this.toast.warning(err.error.error, 'Completá tu perfil');
        } else if (err.status === 400) {
          this.toast.warning(
            'Necesitamos tu título profesional y ciudad antes de buscar ofertas.',
            'Completá tu perfil',
          );
        } else if (err.status === 404) {
          this.toast.warning(
            'No se encontró tu perfil. Por favor creá uno primero.',
            'Perfil no encontrado',
          );
        } else {
          this.toast.error(
            'No pudimos obtener ofertas en este momento. Intentá de nuevo en unos segundos.',
            'Algo falló',
          );
        }
      },
    });
  }
}

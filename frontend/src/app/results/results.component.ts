import { Component} from '@angular/core';
import { CommonModule } from '@angular/common';
import { Title } from '@angular/platform-browser';
import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { JobOffer } from '../models/job-offer.model';
import { JobService } from '../services/job.service';
import { Router, RouterModule } from '@angular/router';
import { environment } from '../../environment/environment';
import { HTMLChangesComponent } from '../shared/html-changes/html-changes';
import { MATCH_THRESHOLDS } from '../constants/match-thresholds';

/**
 * Results component for displaying job offers with filtering
 */
@Component({
  selector: 'app-results',
  imports: [CommonModule, RouterModule],
  standalone: true,
  templateUrl: './results.component.html',
  styleUrls: ['./results.component.scss']
})
export class ResultsComponent {
  offers: JobOffer[] = [];
  hoverState: { [offerId: number]: boolean } = {};
  selectedFilter: 'all' | 'good' | 'regular' | 'bad' = 'all';

  private readonly MATCH_THRESHOLD = MATCH_THRESHOLDS;

  constructor(
    private router: Router,
    private jobService: JobService,
    private titleService: Title,
    private http: HttpClient,
    private changes: HTMLChangesComponent
  ) {
    this.titleService.setTitle('SkilTak - Resultados de Búsqueda');
  }

  /**
   * Initializes component and loads job offers
   */
  ngOnInit(): void {
    this.loadOffers();
  }

  /**
   * Loads job offers from the API
   */
  private loadOffers(): void {
    this.http.get<JobOffer[]>(`${environment.apiUrl}/jobs/jobs-offer/`).subscribe({
      next: (data) => {
        this.offers = Array.isArray(data) ? data : [];
      },
      error: (err: HttpErrorResponse) => {
        console.error('Failed to load job offers:', err);
        this.offers = [];
      }
    });
  }

  /**
   * Returns filtered offers based on selected filter
   */
  get filteredOffer(): JobOffer[] {
    switch (this.selectedFilter) {
      case 'good':
        return this.offers.filter(offer => offer.match_percentage === this.MATCH_THRESHOLD.EXCELLENT);
      case 'regular':
        return this.offers.filter(offer => 
          offer.match_percentage >= this.MATCH_THRESHOLD.GOOD_MIN && 
          offer.match_percentage <= this.MATCH_THRESHOLD.GOOD_MAX
        );
      case 'bad':
        return this.offers.filter(offer => 
          offer.match_percentage >= this.MATCH_THRESHOLD.REGULAR_MIN && 
          offer.match_percentage <= this.MATCH_THRESHOLD.REGULAR_MAX
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

  /**
   * Fetches job offers from scraping service
   */
  obtainOffers(): void {
    this.jobService.getScrapedOffers().subscribe({
      next: (res: JobOffer[]) => {
        this.jobService.setOffers(res);
      },
      error: (err: HttpErrorResponse) => {
        console.error('Error fetching job offers:', err);
      }
    });
  }
}

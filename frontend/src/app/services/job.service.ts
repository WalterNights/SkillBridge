import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable, map } from 'rxjs';

import { environment } from '../../environment/environment';
import { JobOffer } from '../models/job-offer.model';
import { PaginatedResponse } from '../models/paginated-response.model';
import { STORAGE_KEYS } from '../constants/app-stats';

/**
 * Diagnóstico que devuelve el endpoint /scrape/ — útil para ver qué
 * portal trajo cuántas ofertas y cuál (si alguno) falló silenciosamente.
 */
export interface ScrapePortalStat {
  found: number;
  saved_new: number;
  error: string | null;
}

export interface ScrapeResponse {
  offers: JobOffer[];
  scrape_stats: Record<string, ScrapePortalStat>;
}

export interface FilterOptionsResponse {
  countries: { value: string; count: number }[];
  modalities: { value: string; label: string; count: number }[];
}

export interface JobFilters {
  /** Lista de ISO codes (MX, CO, AR…). Vacío = sin filtro. */
  countries: string[];
  /** Lista de modalidades (remote, hybrid, onsite, unknown). Vacío = sin filtro. */
  modalities: string[];
}

/**
 * Service for managing job offers and selected job state
 */
@Injectable({ providedIn: 'root' })
export class JobService {
  private offers: JobOffer[] = [];
  private selectedJob: JobOffer | null = null;

  constructor(private http: HttpClient) {}

  // ---- HTTP ---------------------------------------------------------

  /**
   * Lista las ofertas almacenadas en backend. Desempaqueta la paginación
   * de DRF para devolver `JobOffer[]` directo. Acepta filtros opcionales
   * de país y modalidad (multi-select, comma-separated en query string).
   */
  getJobs(filters?: JobFilters): Observable<JobOffer[]> {
    let url = `${environment.apiUrl}/jobs/jobs/`;
    const params: string[] = [];
    if (filters?.countries?.length) {
      params.push(`country=${filters.countries.join(',')}`);
    }
    if (filters?.modalities?.length) {
      params.push(`modality=${filters.modalities.join(',')}`);
    }
    if (params.length) {
      url += `?${params.join('&')}`;
    }
    return this.http
      .get<PaginatedResponse<JobOffer>>(url)
      .pipe(map((response) => response.results));
  }

  /** Catálogo de filtros disponibles con conteos — para poblar los
   * dropdowns del dashboard. Cacheable en el caller (1 llamada por
   * mount del dashboard). */
  getFilterOptions(): Observable<FilterOptionsResponse> {
    return this.http.get<FilterOptionsResponse>(
      `${environment.apiUrl}/jobs/jobs/filter-options/`,
    );
  }

  /**
   * Detalle de una oferta puntual.
   */
  getJobDetail(id: number | string): Observable<JobOffer> {
    return this.http.get<JobOffer>(`${environment.apiUrl}/jobs/jobs/${id}/`);
  }

  /**
   * Dispara el scrape multi-portal en backend.
   *
   * El response incluye `scrape_stats` con diagnóstico por portal —
   * cuántas ofertas trajo crudas, cuántas eran realmente nuevas, y si
   * alguno falló. El caller puede usar esto para mostrar un breakdown.
   */
  getScrapedOffers(): Observable<ScrapeResponse> {
    return this.http.get<ScrapeResponse>(`${environment.apiUrl}/jobs/jobs/scrape/`);
  }

  // ---- Estado en memoria + session storage --------------------------

  setOffers(data: JobOffer[]): void {
    this.offers = Array.isArray(data) ? data : [];
  }

  getOffers(): JobOffer[] {
    return this.offers;
  }

  clearOffers(): void {
    this.offers = [];
  }

  setSelectedJob(job: JobOffer): void {
    this.selectedJob = job;
    sessionStorage.setItem(STORAGE_KEYS.SELECTED_JOB, JSON.stringify(job));
  }

  getSelectedJob(): JobOffer | null {
    if (this.selectedJob) return this.selectedJob;
    const stored = sessionStorage.getItem(STORAGE_KEYS.SELECTED_JOB);
    return stored ? JSON.parse(stored) : null;
  }

  clearSelectedJob(): void {
    this.selectedJob = null;
    sessionStorage.removeItem(STORAGE_KEYS.SELECTED_JOB);
  }
}

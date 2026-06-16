import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable, map } from 'rxjs';

import { environment } from '../../environment/environment';
import { JobOffer } from '../models/job-offer.model';
import { PaginatedResponse } from '../models/paginated-response.model';
import { STORAGE_KEYS } from '../constants/app-stats';

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
     * de DRF para devolver `JobOffer[]` directo.
     */
    getJobs(): Observable<JobOffer[]> {
        return this.http
            .get<PaginatedResponse<JobOffer>>(`${environment.apiUrl}/jobs/jobs/`)
            .pipe(map(response => response.results));
    }

    /**
     * Detalle de una oferta puntual.
     */
    getJobDetail(id: number | string): Observable<JobOffer> {
        return this.http.get<JobOffer>(`${environment.apiUrl}/jobs/jobs/${id}/`);
    }

    /**
     * Fetches job offers from scraping service
     */
    getScrapedOffers(): Observable<JobOffer[]> {
        return this.http.get<JobOffer[]>(`${environment.apiUrl}/jobs/jobs/scrape/`);
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

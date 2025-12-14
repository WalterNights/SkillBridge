import { Injectable } from "@angular/core";
import { JobOffer } from "../models/job-offer.model";
import { Observable } from "rxjs";
import { HttpClient } from "@angular/common/http";
import { environment } from "../../environment/environment";
import { STORAGE_KEYS } from "../constants/app-stats";

/**
 * Service for managing job offers and selected job state
 */
@Injectable({ providedIn: 'root' })
export class JobService {
    private offers: JobOffer[] = [];
    private selectedJob: JobOffer | null = null;

    constructor(private http: HttpClient) {}

    /**
     * Fetches job offers from scraping service
     * @returns Observable of job offers array
     */
    getScrapedOffers(): Observable<JobOffer[]> {
        return this.http.get<JobOffer[]>(`${environment.apiUrl}/jobs/jobs/scrape/`);
    }

    /**
     * Sets the current job offers
     * @param data - Array of job offers
     */
    setOffers(data: JobOffer[]): void {
        this.offers = Array.isArray(data) ? data : [];
    }

    /**
     * Gets the current job offers
     * @returns Array of job offers
     */
    getOffers(): JobOffer[] {
        return this.offers;
    }

    /**
     * Clears all job offers
     */
    clearOffers(): void {
        this.offers = [];
    }

    /**
     * Sets the selected job and stores it in session storage
     * @param job - Job offer to select
     */
    setSelectedJob(job: JobOffer): void {
        this.selectedJob = job;
        sessionStorage.setItem(STORAGE_KEYS.SELECTED_JOB, JSON.stringify(job));
    }

    /**
     * Gets the selected job from memory or session storage
     * @returns Selected job offer or null
     */
    getSelectedJob(): JobOffer | null {
        if (this.selectedJob) return this.selectedJob;
        const stored = sessionStorage.getItem(STORAGE_KEYS.SELECTED_JOB);
        return stored ? JSON.parse(stored) : null;
    }

    /**
     * Clears the selected job from memory and session storage
     */
    clearSelectedJob(): void {
        this.selectedJob = null;
        sessionStorage.removeItem(STORAGE_KEYS.SELECTED_JOB);
    }
}

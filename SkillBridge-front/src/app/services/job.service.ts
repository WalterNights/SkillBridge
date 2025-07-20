import { Injectable } from "@angular/core";
import { JobOffer } from "../models/job-offer.model";
import { Observable } from "rxjs";
import { HttpClient } from "@angular/common/http";

@Injectable({ providedIn: 'root' })
export class JobService {
    private offers: JobOffer[] = [];
    private selectedJob: JobOffer | null = null;

    constructor(private http: HttpClient) {}

    getScrapedOffers(): Observable<JobOffer[]> {
        return this.http.get<JobOffer[]>('http://localhost:8000/api/jobs/scrap-jobs/');
    }

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
        sessionStorage.setItem('selected_job', JSON.stringify(job));
    }

    getSelectedJob(): JobOffer | null {
        if (this.selectedJob) return this.selectedJob;
        const stored = sessionStorage.getItem('selected_job');
        return stored? JSON.parse(stored) : null;
    }

    clearSelectedJob(): void {
        this.selectedJob = null;
        sessionStorage.removeItem('selected_job');
    }
}
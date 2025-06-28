import { Injectable } from "@angular/core";
import { JobOffer } from "../models/job-offer.model";
import { Observable } from "rxjs";
import { HttpClient } from "@angular/common/http";

@Injectable({ providedIn: 'root' })
export class JobService {
    private offers: JobOffer[] = [];
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
}
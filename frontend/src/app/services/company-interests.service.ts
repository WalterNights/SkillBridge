import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { environment } from '../../environment/environment';

/** Una entrada del inbox del profesional. El email del responsable
 *  solo viene poblado cuando status === 'accepted'. */
export interface CompanyInterestRecord {
  id: number;
  status: 'pending' | 'accepted' | 'dismissed';
  message: string;
  created_at: string;
  updated_at: string;
  company_legal_name: string;
  company_industry: string;
  company_city: string;
  company_country: string;
  company_website: string;
  company_short_description: string;
  company_logo: string;
  responsible_name: string;
  responsible_role: string;
  /** Vacío salvo cuando status === 'accepted'. */
  responsible_email: string;
}

export interface CompanyInterestsList {
  results: CompanyInterestRecord[];
  total: number;
}

export type RespondAction = 'accept' | 'dismiss';

/** Cliente del inbox del profesional. */
@Injectable({ providedIn: 'root' })
export class CompanyInterestsService {
  private http = inject(HttpClient);
  private base = `${environment.apiUrl}/users/me/company-interests`;

  list(statusFilter: 'pending' | 'accepted' | 'dismissed' | 'all' = 'all'): Observable<CompanyInterestsList> {
    const url =
      statusFilter === 'all' ? `${this.base}/` : `${this.base}/?status=${statusFilter}`;
    return this.http.get<CompanyInterestsList>(url);
  }

  respond(interestId: number, action: RespondAction): Observable<CompanyInterestRecord> {
    return this.http.post<CompanyInterestRecord>(
      `${this.base}/${interestId}/respond/`,
      { action },
    );
  }
}

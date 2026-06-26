import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { environment } from '../../environment/environment';

/** Criterios que la empresa define para buscar profesionales.
 *  Matchea el body esperado por `POST /api/companies/search-profiles/`. */
export interface CompanySearchCriteria {
  skills_required: string[];
  target_title: string;
  country?: string;
  min_match?: number;
  limit?: number;
}

/** Shape de cada card de profesional en el feed empresa.
 *  El backend filtra PII activamente — email/telefono/number_id NO
 *  vienen acá nunca. */
export interface ProfileSearchResult {
  profile_id: number;
  first_name: string;
  last_name: string;
  professional_title: string;
  city: string;
  photo_url: string;
  summary: string;
  skills_preview: string[];
  matched_skills: string[];
  missing_skills: string[];
  match_percentage: number;
  title_score?: number;
  skill_score?: number;
}

export interface ProfileSearchResponse {
  results: ProfileSearchResult[];
  total: number;
  /** True cuando el endpoint recibió criterios vacíos — el frontend lo
   *  usa para mostrar empty-state "definí criterios" en vez de "sin
   *  resultados". */
  criteria_empty: boolean;
}

/**
 * Cliente del lado empresa del marketplace. Por ahora solo búsqueda;
 * cuando agreguemos "marcar interés" / inbox, los métodos viven acá.
 */
@Injectable({ providedIn: 'root' })
export class CompanyService {
  private http = inject(HttpClient);
  private base = `${environment.apiUrl}/companies`;

  searchProfiles(criteria: CompanySearchCriteria): Observable<ProfileSearchResponse> {
    return this.http.post<ProfileSearchResponse>(
      `${this.base}/search-profiles/`,
      criteria,
    );
  }
}

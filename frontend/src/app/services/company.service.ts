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

/** Shape del detalle de perfil que la empresa recibe en
 *  GET /api/companies/profiles/{id}/. No incluye PII de contacto. */
export interface ProfileDetail {
  id: number;
  first_name: string;
  last_name: string;
  professional_title: string;
  city: string;
  photo: string | null;
  banner: string | null;
  summary: string;
  skills: string;
  experience: string;
  education: string;
  soft_skills: string;
  languages: string;
  linkedin_url: string | null;
  portfolio_url: string | null;
  has_resume: boolean;
  /** Si esta empresa ya marcó interés antes: 'pending' | 'accepted' |
   *  'dismissed'. Null si nunca lo marcó. */
  interest_status: 'pending' | 'accepted' | 'dismissed' | null;
  interest_marked_at: string | null;
  /** True si la cuenta del request tiene CompanyProfile y puede marcar
   *  interés. False para admin sin company → el UI esconde el botón. */
  can_mark_interest: boolean;
}

export interface CompanyInterestResponse {
  id: number;
  status: 'pending' | 'accepted' | 'dismissed';
  message: string;
  created_at: string;
  updated_at: string;
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

  getProfileDetail(profileId: number): Observable<ProfileDetail> {
    return this.http.get<ProfileDetail>(`${this.base}/profiles/${profileId}/`);
  }

  /** URL absoluta del endpoint del resume — usar como href de `<a download>`.
   *  El backend devuelve un attachment, el browser dispara la descarga.
   *  El JWT viaja via cookies/Authorization vía el interceptor del HttpClient,
   *  pero el `<a download>` regular NO pasa el token: por eso este método
   *  hace fetch como blob y construye una object URL en cliente. */
  downloadResume(profileId: number): Observable<Blob> {
    return this.http.get(`${this.base}/profiles/${profileId}/resume/`, {
      responseType: 'blob',
    });
  }

  markInterest(profileId: number, message: string = ''): Observable<CompanyInterestResponse> {
    return this.http.post<CompanyInterestResponse>(
      `${this.base}/profiles/${profileId}/interest/`,
      { message },
    );
  }
}

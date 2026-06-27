import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { environment } from '../../environment/environment';

/** Criterios opcionales que la empresa define para refinar la búsqueda.
 *  Todos opcionales — si se pasan vacíos, el backend devuelve la lista
 *  completa de profiles visibles (modo NAVEGAR). */
export interface CompanySearchCriteria {
  skills_required?: string[];
  target_title?: string;
  country?: string;
  profession_category?: string;
  min_match?: number;
  limit?: number;
}

/** Shape de cada card de profesional en el feed empresa.
 *  El backend filtra PII activamente — email/telefono/number_id NO
 *  vienen acá nunca.
 *
 *  `match_percentage` es null cuando el endpoint corre en modo NAVEGAR
 *  (sin criterios de match) — el frontend usa esto para esconder el
 *  badge "%" en las cards y mostrar solo info biográfica. */
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
  match_percentage: number | null;
  title_score?: number | null;
  skill_score?: number | null;
}

export interface ProfileSearchResponse {
  results: ProfileSearchResult[];
  total: number;
  /** True si el endpoint no recibió skills ni título — devolvió lista
   *  cruda sin calcular match. */
  criteria_empty: boolean;
  /** Alias semántico de `criteria_empty` desde el rediseño 2026-06-27.
   *  El frontend usa este nombre para decidir qué empty-state mostrar
   *  y si renderizar badges de match%. */
  browse_mode: boolean;
}

/** Cada categoría profesional que tiene perfiles en plataforma. Solo
 *  aparecen las que tienen al menos 1 profile visible — el dropdown del
 *  frontend muestra estas opciones para que cada selección sea
 *  accionable. */
export interface ProfileCategory {
  value: string;   // 'design' | 'tech' | 'marketing' | ...
  label: string;   // 'Diseño' | 'Tecnología' | ...
  count: number;
}

export interface ProfileCategoriesResponse {
  categories: ProfileCategory[];
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

  searchProfiles(criteria: CompanySearchCriteria = {}): Observable<ProfileSearchResponse> {
    return this.http.post<ProfileSearchResponse>(
      `${this.base}/search-profiles/`,
      criteria,
    );
  }

  /** Categorías profesionales presentes en plataforma — fuente del
   *  dropdown smart de filtros. Se llama una sola vez al mount del
   *  dashboard (las categorías cambian lento). */
  getProfileCategories(): Observable<ProfileCategoriesResponse> {
    return this.http.get<ProfileCategoriesResponse>(`${this.base}/profile-categories/`);
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

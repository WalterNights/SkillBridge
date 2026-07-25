import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { environment } from '../../environment/environment';

/** Métricas agregadas del backend para `/admin/stats`. */
export interface AdminStats {
  users: {
    total: number;
    with_profile: number;
    complete_profile: number;
  };
  offers: {
    total: number;
    active: number;
    inactive: number;
    by_portal: { portal: string; count: number }[];
    by_country: { country: string; count: number }[];
  };
  applications: {
    total: number;
    by_status: { status: string; count: number }[];
    success_rate_pct: number;
  };
  ignored: {
    total: number;
  };
}

/** Payload para `PATCH /dashboard/users/{id}/role/`. Ambas keys son
 *  opcionales — sólo se aplican las que vengan. El backend rechaza si
 *  el body llega vacío. */
export interface UserRoleUpdate {
  is_staff?: boolean;
  is_superuser?: boolean;
}

/** Respuesta del endpoint de rol — refleja el estado *después* del save. */
export interface UserRoleResponse {
  id: number;
  username: string;
  email: string;
  is_staff: boolean;
  is_superuser: boolean;
}

/** Cada idioma listado en el perfil. `language` es el nombre legible
 *  (Español, English); `level` puede venir vacío para perfiles legacy. */
export interface ProfileLanguage {
  language: string;
  level: string;
}

/** Fila de motivos globales para /admin/trends. `reason` es "" para las
 *  ignoradas que el user marcó con "Saltar" (retroactivas o skipped). */
export interface TrendsIgnoreReasonRow {
  reason: string;
  count: number;
}

/** Cruce vertical × motivo — alimenta el heatmap/tabla por categoria. */
export interface TrendsIgnoreCategoryRow {
  offer__category: string;
  reason: string;
  count: number;
}

/** Funnel por portal — clicks incluye TODOS los status (pending inclusive).
 *  `conversion_pct` = offer / clicks * 100 redondeado a 1 decimal. */
export interface TrendsPortalFunnelRow {
  portal: string;
  clicks: number;
  applied: number;
  in_review: number;
  interview: number;
  offer: number;
  rejected: number;
  withdrawn: number;
  conversion_pct: number;
}

/** Respuesta completa de /api/dashboard/trends/?days=7|30|90. */
export interface TrendsResponse {
  window_days: number;
  ignore_breakdown: {
    total: number;
    by_reason: TrendsIgnoreReasonRow[];
    by_category_reason: TrendsIgnoreCategoryRow[];
  };
  portal_funnel: TrendsPortalFunnelRow[];
}

/** Detalle profesional ligero de un user — alimenta el modal "Detalles"
 *  en /admin/users. NO incluye experience/education/summary. */
export interface AdminUserProfileDetail {
  user_id: number;
  email: string;
  has_profile: boolean;
  first_name: string;
  last_name: string;
  professional_title: string;
  city: string;
  skills: string[];
  soft_skills: string[];
  languages: ProfileLanguage[];
  linkedin_url: string | null;
  portfolio_url: string | null;
  visible_to_companies: boolean;
}

/**
 * Llamadas a los endpoints admin (`/api/dashboard/*`). Todas están
 * protegidas por `IsAdminUser` en el backend — los users sin `is_staff`
 * reciben 403 incluso si el AdminGuard del router falla.
 */
@Injectable({ providedIn: 'root' })
export class AdminService {
  private http = inject(HttpClient);

  getStats(): Observable<AdminStats> {
    return this.http.get<AdminStats>(`${environment.apiUrl}/dashboard/stats/`);
  }

  /** Tendencias de comportamiento (motivos de ignore + funnel por portal)
   *  para /admin/trends. `days` acepta 7 | 30 | 90; el backend clampea
   *  otros valores a 30. */
  getTrends(days: number = 30): Observable<TrendsResponse> {
    return this.http.get<TrendsResponse>(
      `${environment.apiUrl}/dashboard/trends/?days=${days}`,
    );
  }

  /** Promueve o degrada a un user. `userId` es el id del modelo User
   *  (NO del UserProfile). El backend valida self-demote y exige
   *  superuser para tocar `is_superuser`. */
  updateUserRole(userId: number, payload: UserRoleUpdate): Observable<UserRoleResponse> {
    return this.http.patch<UserRoleResponse>(
      `${environment.apiUrl}/dashboard/users/${userId}/role/`,
      payload,
    );
  }

  /** Detalle profesional ligero — alimenta el modal "Detalles" en
   *  /admin/users. Foco en skills/idiomas/links; NO trae experience
   *  ni education (densos, no aportan a la decisión rápida del admin). */
  getUserProfileDetail(userId: number): Observable<AdminUserProfileDetail> {
    return this.http.get<AdminUserProfileDetail>(
      `${environment.apiUrl}/dashboard/users/${userId}/profile-detail/`,
    );
  }
}

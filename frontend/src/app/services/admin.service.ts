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

/**
 * Llamadas al endpoint admin (`/api/dashboard/stats/`). Acceso protegido
 * por `IsAdminUser` en el backend — los users sin `is_staff` reciben 403.
 */
@Injectable({ providedIn: 'root' })
export class AdminService {
  private http = inject(HttpClient);

  getStats(): Observable<AdminStats> {
    return this.http.get<AdminStats>(`${environment.apiUrl}/dashboard/stats/`);
  }
}

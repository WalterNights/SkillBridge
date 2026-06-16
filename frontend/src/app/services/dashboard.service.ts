import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable, map } from 'rxjs';

import { environment } from '../../environment/environment';
import { PaginatedResponse } from '../models/paginated-response.model';
import { User } from '../models/user.model';

/**
 * Llamadas al endpoint `/api/dashboard/`.
 *
 * El endpoint devuelve respuesta paginada de DRF; este servicio
 * desempaqueta `results` para que el componente reciba `User[]` directo.
 */
@Injectable({ providedIn: 'root' })
export class DashboardService {
  constructor(private http: HttpClient) {}

  getUsers(): Observable<User[]> {
    return this.http
      .get<PaginatedResponse<User>>(`${environment.apiUrl}/dashboard/`)
      .pipe(map(response => response.results));
  }
}

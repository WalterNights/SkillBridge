import { HttpClient } from '@angular/common/http';
import { Injectable, inject, signal } from '@angular/core';
import { Observable, map, of, tap } from 'rxjs';

import { environment } from '../../environment/environment';

/** Diccionario plano `{key: bool}` que devuelve el endpoint público
 *  `/api/system/feature-flags/`. Las keys son las definidas en data
 *  migration del backend. Si un flag no está en la respuesta, se asume
 *  apagado — así código nuevo que lee un flag no rompe en un ambiente
 *  donde la migración todavía no corrió. */
export type FeatureFlags = Record<string, boolean>;

/** Payload del endpoint admin (`/api/system/admin/feature-flags/`).
 *  `key` es read-only en el backend — los flags se crean en data
 *  migration, no via API. */
export interface SystemSetting {
  id: number;
  key: string;
  value_bool: boolean;
  description: string;
  updated_at: string;
}

/**
 * Service que cachea los feature flags públicos para que cualquier
 * componente los lea sin disparar request adicional. Hace UNA llamada al
 * boot del shell y deja el resultado en un signal.
 *
 * No requiere auth — el endpoint público es legible por el SPA antes del
 * login (la pantalla de login podría depender de un flag a futuro).
 *
 * Para la UI admin se usa el método `listAdmin`/`updateAdmin` que sí
 * pegan al endpoint protegido (IsAdminUser).
 */
@Injectable({ providedIn: 'root' })
export class FeatureFlagsService {
  private http = inject(HttpClient);

  /** Flags públicos cacheados. `null` antes del primer load para que el
   *  caller pueda distinguir "todavía no cargué" de "cargué y vino vacío".
   *  Una vez cargado, queda en memoria hasta que el user recargue la
   *  página — los flags cambian poco y no vale polling. */
  private flagsSignal = signal<FeatureFlags | null>(null);

  /** Lectura no-bloqueante: lee el flag del cache. Devuelve `false` si
   *  no cargó todavía o el flag no existe — defensivo, así un componente
   *  nuevo no espera el load para renderizar la UI default (sin el flag). */
  isEnabled(key: string): boolean {
    const flags = this.flagsSignal();
    return Boolean(flags?.[key]);
  }

  /** Signal raw para componentes que necesiten reaccionar al cambio
   *  (ej. checkbox que aparece/desaparece después del bootstrap). */
  readonly flags = this.flagsSignal.asReadonly();

  /** Trigger del load — llamado una vez desde el bootstrap del shell.
   *  Si ya está cargado, no hace nada (caching de la primera respuesta).
   *  No tira en error — un fallo no debe romper el shell, simplemente
   *  los flags quedan vacíos y todos los `isEnabled` devuelven false. */
  loadPublic(): Observable<FeatureFlags> {
    if (this.flagsSignal() !== null) {
      return of(this.flagsSignal()!);
    }
    return this.http
      .get<FeatureFlags>(`${environment.apiUrl}/system/feature-flags/`)
      .pipe(
        tap({
          next: (flags) => this.flagsSignal.set(flags ?? {}),
          error: () => this.flagsSignal.set({}),
        }),
      );
  }

  /** Lista los flags para la UI admin. NO usa el cache público — el
   *  admin necesita la descripción + updated_at, no solo el bool. */
  listAdmin(): Observable<SystemSetting[]> {
    return this.http
      .get<{ results: SystemSetting[] } | SystemSetting[]>(
        `${environment.apiUrl}/system/admin/feature-flags/`,
      )
      .pipe(
        // DRF pagina por default → unwrappeamos `results` cuando viene.
        // En desarrollo a veces no pagina (PAGE_SIZE > count) y devuelve
        // el array crudo — soportamos ambos formatos.
        map((response) =>
          Array.isArray(response) ? response : response.results ?? [],
        ),
      );
  }

  /** Toggle de un flag. Después de actualizar, invalida el cache público
   *  para que el próximo `loadPublic()` traiga el nuevo valor. Idempotente:
   *  si el usuario clickea twice, el backend acepta el segundo PATCH y
   *  devuelve 200 igual. */
  updateAdmin(key: string, valueBool: boolean): Observable<SystemSetting> {
    return this.http
      .patch<SystemSetting>(
        `${environment.apiUrl}/system/admin/feature-flags/${key}/`,
        { value_bool: valueBool },
      )
      .pipe(
        tap((updated) => {
          // Refrescar el cache local optimísticamente para que el resto
          // del SPA reaccione sin esperar al próximo reload.
          const current = this.flagsSignal() ?? {};
          this.flagsSignal.set({ ...current, [updated.key]: updated.value_bool });
        }),
      );
  }
}

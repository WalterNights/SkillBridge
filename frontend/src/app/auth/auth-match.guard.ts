import { inject } from '@angular/core';
import { CanMatchFn } from '@angular/router';

import { AuthService } from './auth.service';

/**
 * CanMatch guard — devuelve true SOLO si el user está autenticado.
 *
 * Diferencia clave con AutoGuard (canActivate):
 *   - canActivate: bouncea unauth a login (este flujo es deseable para
 *     /dashboard, /cv, etc — rutas privadas puras).
 *   - canMatch: si falla, la ruta NO matchea, el router prueba la
 *     siguiente. Útil para rutas con FALLBACK PÚBLICO (/recursos,
 *     /blog) — auth → wrap en shell; unauth → fallback público sin
 *     redirigir a login.
 */
export const authMatchGuard: CanMatchFn = () => {
  return inject(AuthService).isAuthenticated();
};

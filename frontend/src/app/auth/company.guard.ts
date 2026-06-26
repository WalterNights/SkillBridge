import { Injectable } from '@angular/core';
import { CanActivate, Router } from '@angular/router';
import { AuthService } from './auth.service';

/**
 * Gate para rutas /company/*.
 *
 * Lee `account_type` del JWT cacheado en storage por AuthService.
 * - Si el user no está logueado → /auth/login (AutoGuard lo manejaría
 *   pero defensivamente lo hacemos también acá).
 * - Si es professional sin staff → /dashboard (no le sirve la vista).
 * - Si es company → permitir.
 * - Si es admin (is_staff=True, aunque sea profesional) → permitir
 *   read-only para soporte/curaduría. El componente esconde "Marcar
 *   interés" si no tiene CompanyProfile (flag `can_mark_interest`
 *   del backend).
 *
 * Este guard es el espejo de AdminGuard: defensa en profundidad sobre
 * el split que el AppShell ya hace via *ngIf="isCompany()".
 */
@Injectable({ providedIn: 'root' })
export class CompanyGuard implements CanActivate {
  constructor(
    private authService: AuthService,
    private router: Router,
  ) {}

  canActivate(): boolean {
    if (!this.authService.isAuthenticated()) {
      this.router.navigate(['/auth/login']);
      return false;
    }
    if (this.authService.isCompany() || this.authService.isAdmin()) {
      return true;
    }
    // Cuenta profesional sin staff intentando entrar a /company/* —
    // al dashboard.
    this.router.navigate(['/dashboard']);
    return false;
  }
}

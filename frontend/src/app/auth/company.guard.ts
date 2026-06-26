import { Injectable } from '@angular/core';
import { CanActivate, Router } from '@angular/router';
import { AuthService } from './auth.service';

/**
 * Gate para rutas /company/*.
 *
 * Lee `account_type` del JWT cacheado en storage por AuthService.
 * - Si el user no está logueado → /auth/login (AutoGuard lo manejaría
 *   pero defensivamente lo hacemos también acá).
 * - Si es professional → /dashboard (no le sirve la vista empresa).
 * - Si es company → permitir.
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
    if (this.authService.isCompany()) {
      return true;
    }
    // Cuenta profesional intentando entrar a /company/* — al dashboard.
    this.router.navigate(['/dashboard']);
    return false;
  }
}

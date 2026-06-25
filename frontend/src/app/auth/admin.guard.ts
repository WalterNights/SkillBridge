import { Injectable } from '@angular/core';
import { CanActivate, Router } from '@angular/router';
import { AuthService } from './auth.service';

/**
 * Gate para rutas /admin/*.
 *
 * Lee el flag `is_staff` que el backend escupe en el payload del JWT
 * login y AuthService cachea en storage. Rechazo redirige a /dashboard
 * (no a /auth/login porque el user ya está autenticado — solo no tiene
 * permisos de admin). No reescribimos el sidebar de admin acá: el
 * AppShell ya esconde el grupo con *ngIf="isAdmin()", esto es la
 * defensa en profundidad para que un /admin/users tipeado a mano por
 * un user normal no abra la vista.
 */
@Injectable({ providedIn: 'root' })
export class AdminGuard implements CanActivate {
  constructor(
    private authService: AuthService,
    private router: Router,
  ) {}

  canActivate(): boolean {
    if (this.authService.isAdmin()) {
      return true;
    }
    this.router.navigate(['/dashboard']);
    return false;
  }
}

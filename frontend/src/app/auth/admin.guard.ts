import { Injectable } from '@angular/core';
import { CanActivate, Router } from '@angular/router';
import { AuthService } from './auth.service';

/**
 * Gate for /admin/* routes.
 *
 * The backend doesn't expose a `role` claim in the JWT yet, so for
 * now the guard rejects everyone. Replace `isAdmin()` once the
 * backend ships the claim (likely `is_staff` from Django's default).
 *
 * Why ship a guard that always rejects: the /admin/* routes have to
 * exist from Phase 1 so the AppShell can render the admin sidebar
 * without dead links in other screens.
 */
@Injectable({ providedIn: 'root' })
export class AdminGuard implements CanActivate {
  constructor(
    private authService: AuthService,
    private router: Router,
  ) {}

  canActivate(): boolean {
    if (this.isAdmin()) {
      return true;
    }
    this.router.navigate(['/dashboard']);
    return false;
  }

  /** Placeholder until the backend returns the role in the JWT. */
  private isAdmin(): boolean {
    // TODO: read JWT claim (is_staff / is_superuser) or call /users/me/
    // and cache the role inside AuthService.
    return false;
  }
}

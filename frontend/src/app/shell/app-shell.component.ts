import { CommonModule } from '@angular/common';
import { Component, DestroyRef, HostListener, computed, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { Router, RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';
import { AuthService } from '../auth/auth.service';

/**
 * Wrapper for authenticated routes (/dashboard, /jobs/:id, /profile,
 * /cv, /settings, /admin/*).
 *
 * Renders a minimal sidebar ("Inicio" + Tip card) and a topbar with
 * search/CTAs and a user dropdown. Page content is projected through
 * the `<router-outlet>`.
 *
 * On mobile (<lg) the sidebar collapses into a drawer toggled by the
 * hamburger in the topbar.
 *
 * When the admin role lands, this shell will conditionally render the
 * admin sidebar (with extra items) instead of the minimal user one.
 */
@Component({
  selector: 'app-shell',
  standalone: true,
  imports: [CommonModule, RouterOutlet, RouterLink, RouterLinkActive],
  templateUrl: './app-shell.component.html',
  styleUrl: './app-shell.component.scss',
})
export class AppShellComponent {
  /** Mobile drawer open state. Ignored on desktop. */
  drawerOpen = signal(false);

  /** Top-right user dropdown open state. */
  userMenuOpen = signal(false);

  /**
   * Reactive user display data. Re-reads from storage whenever
   * AuthService emits a login state change so the topbar stays
   * in sync with logout/login without a hard reload.
   */
  userName = signal(this.auth.getUserName());
  userEmail = signal(this.auth.getUserEmail());
  userInitial = computed(() => this.userName().charAt(0).toUpperCase() || 'U');

  private destroyRef = inject(DestroyRef);

  constructor(
    private auth: AuthService,
    private router: Router,
  ) {
    this.auth.isLoggedIn$.pipe(takeUntilDestroyed(this.destroyRef)).subscribe(() => {
      this.userName.set(this.auth.getUserName());
      this.userEmail.set(this.auth.getUserEmail());
    });
  }

  toggleDrawer(open?: boolean): void {
    this.drawerOpen.set(open ?? !this.drawerOpen());
  }

  toggleUserMenu(event?: MouseEvent): void {
    event?.stopPropagation();
    this.userMenuOpen.set(!this.userMenuOpen());
  }

  @HostListener('document:click')
  closeUserMenu(): void {
    if (this.userMenuOpen()) {
      this.userMenuOpen.set(false);
    }
  }

  logout(): void {
    this.auth.logout();
    this.userMenuOpen.set(false);
    this.router.navigate(['/']);
  }
}

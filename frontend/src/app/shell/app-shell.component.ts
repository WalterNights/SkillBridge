import { CommonModule } from '@angular/common';
import { Component, DestroyRef, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';
import { AuthService } from '../auth/auth.service';
import { TipService } from '../services/tip.service';
import { UserNavComponent } from '../shared/user-nav/user-nav.component';
import { getTipOfTheDay as getStaticTipOfTheDay } from './daily-tips';

const SIDEBAR_COLLAPSED_KEY = 'shell_sidebar_collapsed';

/**
 * Wrapper for authenticated routes (/dashboard, /jobs/:id, /settings,
 * /admin/*). Renders a slim collapsible sidebar with utility nav for
 * both user and admin roles, plus a topbar that delegates the bell +
 * avatar dropdown to the shared `<app-user-nav>` widget (so the same
 * chrome shows on landing, /profile, /cv too).
 *
 * On mobile (<lg) the sidebar collapses into a drawer toggled by the
 * hamburger in the topbar. On desktop the user can collapse the
 * sidebar to icon-only width — preference persisted in localStorage.
 *
 * `/profile` and `/cv` are NOT wrapped in this shell — they're
 * full-page editorial layouts with their own header.
 */
@Component({
  selector: 'app-shell',
  standalone: true,
  imports: [CommonModule, RouterOutlet, RouterLink, RouterLinkActive, UserNavComponent],
  templateUrl: './app-shell.component.html',
  styleUrl: './app-shell.component.scss',
})
export class AppShellComponent {
  private auth = inject(AuthService);
  private tipApi = inject(TipService);
  private destroyRef = inject(DestroyRef);

  /** Mobile drawer open state. Ignored on desktop. */
  drawerOpen = signal(false);

  /** Desktop sidebar collapsed (icon-only) state. Persisted to localStorage. */
  sidebarCollapsed = signal(localStorage.getItem(SIDEBAR_COLLAPSED_KEY) === 'true');

  /** Tip de hoy para el widget del sidebar.
   *
   * Inicializo con el static (sync, instantáneo, sin flicker en first
   * paint) y después dejo que el service intente refrescar desde el
   * endpoint. Si el endpoint trae uno distinto (porque el pool de DB
   * incluye tips AI-generated nuevos), reemplazo. Si falla, se queda
   * con el static que ya estaba.
   */
  tipOfTheDay = signal(getStaticTipOfTheDay());

  constructor() {
    this.tipApi
      .getTipOfTheDay()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe((text) => this.tipOfTheDay.set(text));
  }

  /**
   * Whether the current user has admin privileges. Placeholder until
   * the backend role flag lands — once `AuthService` exposes a real
   * role, swap this default out.
   */
  isAdmin = signal(false);

  toggleDrawer(open?: boolean): void {
    this.drawerOpen.set(open ?? !this.drawerOpen());
  }

  toggleCollapse(): void {
    const next = !this.sidebarCollapsed();
    this.sidebarCollapsed.set(next);
    localStorage.setItem(SIDEBAR_COLLAPSED_KEY, String(next));
  }
}

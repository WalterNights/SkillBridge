import { filter } from 'rxjs';
import { CommonModule } from '@angular/common';
import { AuthService } from './auth/auth.service';
import { HeaderComponent } from './header/header.component';
import { Component, OnInit, inject } from '@angular/core';
import { Router, RouterOutlet, NavigationEnd } from '@angular/router';
import { AnalyticsService } from './services/analytics.service';
import { ToastContainerComponent } from './shared/molecules/toast-container/toast-container.component';

/**
 * Root shell. Only renders the legacy public `<app-header>` for the
 * handful of old auth flows that haven't been ported yet
 * (`/auth/forgot-password`, `/auth/reset-password`). Everything else
 * either has its own header (landing, login, register, profile, cv)
 * or lives inside the AppShell (dashboard, jobs/:id, settings, admin).
 */
@Component({
  selector: 'app-root',
  imports: [CommonModule, RouterOutlet, HeaderComponent, ToastContainerComponent],
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.scss'],
})
export class AppComponent implements OnInit {
  title = 'SkilTak-front';
  showHeader = false;

  private analytics = inject(AnalyticsService);

  /** Routes that still rely on the legacy <app-header>. Stripped down
   *  as each route gets its own header during the redesign. */
  private legacyHeaderRoutes = ['/auth/forgot-password', '/auth/reset-password'];

  constructor(
    private authService: AuthService,
    private router: Router,
  ) {
    this.router.events
      .pipe(filter((event) => event instanceof NavigationEnd))
      .subscribe((event: any) => {
        this.showHeader = this.legacyHeaderRoutes.some((path) =>
          event.urlAfterRedirects.startsWith(path),
        );
      });

    // Auto-track pageviews via Router events. Idempotente — el service
    // sólo se suscribe la primera vez.
    this.analytics.init(this.router);
  }

  ngOnInit(): void {
    this.authService.syncAuthStatus();
  }
}

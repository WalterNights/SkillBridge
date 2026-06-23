import { CommonModule } from '@angular/common';
import { Component, DestroyRef, computed, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { Router, RouterLink, RouterLinkActive } from '@angular/router';

import { AuthService } from '../../auth/auth.service';
import { UserNavComponent } from '../user-nav/user-nav.component';

/**
 * Navbar para las páginas públicas de marketing (/, /como-funciona,
 * /recursos, /recursos/:slug). Comparte el chrome para que la
 * experiencia de navegación se sienta consistente entre vistas.
 *
 * Logged out: muestra "Ingresar" + CTA "Empezar".
 * Logged in:  muestra el avatar dropdown via <app-user-nav>.
 */
@Component({
  selector: 'app-public-nav',
  standalone: true,
  imports: [CommonModule, RouterLink, RouterLinkActive, UserNavComponent],
  templateUrl: './public-nav.component.html',
  styleUrl: './public-nav.component.scss',
})
export class PublicNavComponent {
  private auth = inject(AuthService);
  private router = inject(Router);
  private destroyRef = inject(DestroyRef);

  isLoggedIn = signal(this.auth.isAuthenticated());
  isProfileComplete = signal(this.auth.isProfileComplete$);

  /** El CTA "Empezar/Ir al dashboard" cambia label según el estado. */
  ctaLabel = computed(() => (this.isLoggedIn() ? 'Ir al dashboard' : 'Empezar'));

  constructor() {
    this.auth.isLoggedIn$.pipe(takeUntilDestroyed(this.destroyRef)).subscribe((loggedIn) => {
      this.isLoggedIn.set(loggedIn);
    });
  }

  /** CTA: si está logueado va al dashboard, sino arranca el wizard. */
  startProfile(): void {
    if (this.isLoggedIn()) {
      this.router.navigate(['/dashboard']);
    } else {
      this.router.navigate(['/auth/register']);
    }
  }
}

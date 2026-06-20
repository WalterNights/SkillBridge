import { CommonModule } from '@angular/common';
import { Component, inject, signal } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { Title } from '@angular/platform-browser';
import { Router, RouterLink } from '@angular/router';
import { AuthService } from '../auth/auth.service';
import { STORAGE_KEYS } from '../constants/app-stats';
import { RevealDirective } from '../shared/directives/reveal.directive';

/**
 * Where the landing CTA should send users right after they sign up.
 * Stored under STORAGE_KEYS.REDIRECT_AFTER_LOGIN so /auth/login picks
 * it up after credentials are entered.
 */
const POST_SIGNUP_REDIRECT = '/profile';

type AnchorId = 'como-funciona' | 'recursos' | 'blog';

/**
 * Public landing page (/). Not behind AutoGuard.
 *
 * The primary CTA "Crear mi perfil" is role-aware:
 *   - logged out                  → /auth/register
 *   - logged in, profile pending  → /profile
 *   - logged in, profile complete → /dashboard (skip the intro)
 */
@Component({
  selector: 'app-home',
  standalone: true,
  imports: [CommonModule, RouterLink, RevealDirective],
  templateUrl: './home.component.html',
  styleUrl: './home.component.scss',
})
export class HomeComponent {
  private auth = inject(AuthService);
  private router = inject(Router);

  /**
   * Signals derived from AuthService observables. `toSignal` handles
   * the subscription teardown automatically when the component is
   * destroyed, no manual unsubscribe needed.
   */
  isLoggedIn = toSignal(this.auth.isLoggedIn$, { initialValue: false });
  profileComplete = toSignal(this.auth.isProfileComplete$, { initialValue: false });

  /** Active anchor in the navbar, updated on click. */
  currentSection = signal<AnchorId | null>(null);

  constructor(title: Title) {
    title.setTitle('SkilTak — Encontrá tu próximo paso');
  }

  /** Navbar link click: mark as active + smooth-scroll to the section. */
  setSection(id: AnchorId, event: MouseEvent): void {
    event.preventDefault();
    this.currentSection.set(id);
    document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  /** Primary CTA shared by hero, navbar and final block. */
  startProfile(): void {
    if (!this.isLoggedIn()) {
      sessionStorage.setItem(STORAGE_KEYS.REDIRECT_AFTER_LOGIN, POST_SIGNUP_REDIRECT);
      this.router.navigate(['/auth/register']);
      return;
    }
    this.router.navigate([this.profileComplete() ? '/dashboard' : '/profile']);
  }
}

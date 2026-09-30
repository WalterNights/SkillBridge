import { CommonModule } from '@angular/common';
import { Component, computed, inject, signal } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { Title } from '@angular/platform-browser';
import { Router, RouterLink } from '@angular/router';
import { AuthService } from '../auth/auth.service';
import { STORAGE_KEYS } from '../constants/app-stats';
import { AnalyticsService } from '../services/analytics.service';
import { LandingReview, ReviewService } from '../services/review.service';
import { RevealDirective } from '../shared/directives/reveal.directive';
import { PublicFooterComponent } from '../shared/public-footer/public-footer.component';
import { UserNavComponent } from '../shared/user-nav/user-nav.component';

/**
 * Where the landing CTA should send users right after they sign up.
 * Stored under STORAGE_KEYS.REDIRECT_AFTER_LOGIN so /auth/login picks
 * it up after credentials are entered.
 */
const POST_SIGNUP_REDIRECT = '/profile';

type AnchorId = 'como-funciona' | 'recursos' | 'blog';

/** Reseñas reales que se muestran en el landing (una fila de 3 columnas). */
const LANDING_REVIEWS_SHOWN = 3;

/** Tarjeta de testimonio real, con las iniciales precalculadas para el
 * avatar cuando el usuario no subió foto. */
type LandingReviewCard = LandingReview & { initials: string };

function toInitials(name: string): string {
  return name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0].toUpperCase())
    .join('');
}

/**
 * Snippet de feedback positivo que se renderiza en el bloque final del
 * landing cuando el usuario está logueado (en lugar del CTA "Empezar",
 * que ya no le aporta a alguien dentro del producto). El stub se usa
 * solo mientras `/api/reviews/landing/` no devuelva reseñas reales.
 */
interface UserComment {
  quote: string;
  name: string;
  role: string;
  city: string;
  rating: number;
}

const POSITIVE_COMMENTS_STUB: UserComment[] = [
  {
    quote:
      'Conseguí tres entrevistas en una semana sin tener que saltar entre cinco bolsas distintas.',
    name: 'Camila R.',
    role: 'Diseñadora UX',
    city: 'Bogotá',
    rating: 5,
  },
  {
    quote: 'El match con mi CV me ahorra horas filtrando ofertas que no calzan con mi stack.',
    name: 'Diego M.',
    role: 'Backend Developer',
    city: 'Medellín',
    rating: 5,
  },
  {
    quote: 'Subí mi CV y en dos minutos tenía mi perfil completo. Nunca había visto algo así.',
    name: 'Valeria S.',
    role: 'Product Manager',
    city: 'Buenos Aires',
    rating: 5,
  },
];

/**
 * Public landing page (/). Not behind AutoGuard.
 *
 * El bloque final del landing es role-aware:
 *   - logged out → CTA "Empezar" para registrarse
 *   - logged in  → muro de comentarios positivos de la comunidad
 * Los demás CTAs ("Crear mi perfil", "Empezar") cuando hay sesión activa
 * van directo al dashboard sin pasar por register/profile.
 */
@Component({
  selector: 'app-home',
  standalone: true,
  imports: [CommonModule, RouterLink, RevealDirective, PublicFooterComponent, UserNavComponent],
  templateUrl: './home.component.html',
  styleUrl: './home.component.scss',
})
export class HomeComponent {
  private auth = inject(AuthService);
  private router = inject(Router);
  private analytics = inject(AnalyticsService);
  private reviewService = inject(ReviewService);

  /**
   * Signals derived from AuthService observables. `toSignal` handles
   * the subscription teardown automatically when the component is
   * destroyed, no manual unsubscribe needed.
   */
  isLoggedIn = toSignal(this.auth.isLoggedIn$, { initialValue: false });
  profileComplete = toSignal(this.auth.isProfileComplete$, { initialValue: false });

  /** Active anchor in the navbar, updated on click. */
  currentSection = signal<AnchorId | null>(null);

  /** Reseñas reales aprobadas (4-5 estrellas, con consentimiento).
   * Vacío mientras carga o si no hay ninguna — en ese caso el template
   * sigue mostrando los testimonios estáticos. */
  landingReviews = signal<LandingReview[]>([]);

  landingCards = computed<LandingReviewCard[]>(() =>
    this.landingReviews()
      .slice(0, LANDING_REVIEWS_SHOWN)
      .map((r) => ({ ...r, initials: toInitials(r.name) })),
  );

  /** Comentarios del bloque final para usuarios logueados: reseñas
   * reales si existen, stub si todavía no hay. */
  positiveComments = computed<readonly UserComment[]>(() => {
    const cards = this.landingCards();
    if (cards.length === 0) return POSITIVE_COMMENTS_STUB;
    return cards.map((r) => ({
      quote: r.comment,
      name: r.name,
      role: r.role,
      city: r.city,
      rating: r.rating,
    }));
  });

  constructor(title: Title) {
    title.setTitle('SkilTak — Deja de buscar en mil portales');
    this.reviewService.landing().subscribe({
      next: (reviews) => this.landingReviews.set(reviews),
      // Silencioso: sin reseñas el landing cae a los testimonios estáticos.
      error: () => {},
    });
  }

  /** Navbar link click: mark as active + smooth-scroll to the section. */
  setSection(id: AnchorId, event: MouseEvent): void {
    event.preventDefault();
    this.currentSection.set(id);
    document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  /**
   * Primary CTA shared by hero + navbar.
   *
   * Logueado → al dashboard directo (no tiene sentido empujar a
   * register o profile a alguien que ya entró). Sin sesión → register,
   * dejando memoria del intent para que el login post-register lo lleve
   * a /profile a completar la info.
   */
  startProfile(): void {
    if (this.isLoggedIn()) {
      this.analytics.trackClick('home_cta_dashboard');
      this.router.navigate(['/dashboard']);
      return;
    }
    this.analytics.trackClick('home_cta_register');
    sessionStorage.setItem(STORAGE_KEYS.REDIRECT_AFTER_LOGIN, POST_SIGNUP_REDIRECT);
    this.router.navigate(['/auth/register']);
  }
}

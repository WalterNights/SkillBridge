import { CommonModule } from '@angular/common';
import { Component, inject, signal } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { Title } from '@angular/platform-browser';
import { Router, RouterLink } from '@angular/router';
import { AuthService } from '../auth/auth.service';
import { STORAGE_KEYS } from '../constants/app-stats';
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

/**
 * Snippet de feedback positivo que se renderiza en el bloque final del
 * landing cuando el usuario está logueado (en lugar del CTA "Empezar",
 * que ya no le aporta a alguien dentro del producto). Texto stub hasta
 * que tengamos backend de comentarios — cuando esté, swappearlo por un
 * fetch al endpoint `top-positive` y ordenar por rating desc.
 */
interface UserComment {
  quote: string;
  name: string;
  role: string;
  city: string;
  rating: 5;
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

  /**
   * Signals derived from AuthService observables. `toSignal` handles
   * the subscription teardown automatically when the component is
   * destroyed, no manual unsubscribe needed.
   */
  isLoggedIn = toSignal(this.auth.isLoggedIn$, { initialValue: false });
  profileComplete = toSignal(this.auth.isProfileComplete$, { initialValue: false });

  /** Active anchor in the navbar, updated on click. */
  currentSection = signal<AnchorId | null>(null);

  /** Comentarios positivos para el bloque final cuando el usuario está
   * logueado. Stub hasta que exista el backend de comentarios. */
  positiveComments: readonly UserComment[] = POSITIVE_COMMENTS_STUB;

  constructor(title: Title) {
    title.setTitle('SkilTak — Deja de buscar en mil portales');
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
      this.router.navigate(['/dashboard']);
      return;
    }
    sessionStorage.setItem(STORAGE_KEYS.REDIRECT_AFTER_LOGIN, POST_SIGNUP_REDIRECT);
    this.router.navigate(['/auth/register']);
  }
}

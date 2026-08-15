import {
  Component,
  ElementRef,
  HostBinding,
  NgZone,
  OnDestroy,
  OnInit,
  effect,
  inject,
  viewChild,
} from '@angular/core';
import { Title, Meta } from '@angular/platform-browser';

import { PortfolioI18nService } from './i18n/portfolio-i18n.service';
import { PortfolioService } from './portfolio.service';
import { PortfolioSidebarComponent } from './components/sidebar.component';
import { HeroSectionComponent } from './sections/hero.component';
import { AboutSectionComponent } from './sections/about.component';
import { ExperienceSectionComponent } from './sections/experience.component';
import { ProjectsSectionComponent } from './sections/projects.component';
import { ContactSectionComponent } from './sections/contact.component';

const PORTFOLIO_SLUG = 'walternightsdev';

/**
 * Ruta pública /portafolio/walternightsdev.
 *
 * Renderiza FUERA del AppShell de SkilTak (ver app.routes.ts): no hay
 * <app-header>, sidebar de usuario, ni footer del SPA. El visitante ve
 * un sitio de identidad propia (fondo, tipografía y grid distintos) pero
 * reusa Tailwind y el pipeline de Angular existente.
 *
 * El aislamiento visual se logra con CSS variables scopeadas al selector
 * `app-portfolio-shell` en el .scss — todos los tokens (color, fuente,
 * ritmo) viven ahí y no se filtran al resto del SPA.
 */
@Component({
  selector: 'app-portfolio-shell',
  standalone: true,
  imports: [
    PortfolioSidebarComponent,
    HeroSectionComponent,
    AboutSectionComponent,
    ExperienceSectionComponent,
    ProjectsSectionComponent,
    ContactSectionComponent,
  ],
  templateUrl: './portfolio-shell.component.html',
  styleUrl: './portfolio-shell.component.scss',
})
export class PortfolioShellComponent implements OnInit, OnDestroy {
  readonly i18n = inject(PortfolioI18nService);
  private readonly portfolio = inject(PortfolioService);
  private readonly title = inject(Title);
  private readonly meta = inject(Meta);
  private readonly zone = inject(NgZone);

  /** Referencia al div del cursor-glow. El CSS lee las CSS vars
   *  --pf-mx / --pf-my desde este elemento para posicionar el
   *  radial-gradient donde está el mouse. */
  private readonly cursorGlow = viewChild<ElementRef<HTMLDivElement>>('cursorGlow');

  private mouseMoveHandler: ((e: MouseEvent) => void) | null = null;

  @HostBinding('class') hostClass = 'portfolio-scope';

  constructor() {
    // Actualiza <title> y meta description al togglear idioma.
    effect(() => {
      const dict = this.i18n.dict();
      this.title.setTitle(dict.meta.title);
      this.meta.updateTag({ name: 'description', content: dict.meta.description });
      document.documentElement.setAttribute('lang', this.i18n.lang());
    });
  }

  ngOnInit(): void {
    // Fetch del contenido editable desde el backend. Si responde 200,
    // los diccionarios sobreescriben los bundled. Si 404 o falla de red,
    // seguimos con los bundled (fallback graceful) y el sitio no queda
    // en blanco. No bloqueamos el render inicial: los signals del i18n
    // service actualizan los componentes automáticamente cuando llega
    // la respuesta.
    this.portfolio.getPublic(PORTFOLIO_SLUG).subscribe({
      next: (payload) => {
        this.i18n.applyBackendContent({
          es: payload.content,
          en: payload.content_en,
          images: payload.images,
        });
      },
      error: () => {
        // Silencioso — bundled JSON queda como fallback. Ver
        // portfolio-i18n.service.ts para el mecanismo de override.
      },
    });

    this.attachCursorGlow();
  }

  ngOnDestroy(): void {
    if (this.mouseMoveHandler) {
      window.removeEventListener('mousemove', this.mouseMoveHandler);
      this.mouseMoveHandler = null;
    }
  }

  /** Cursor glow: escucha `mousemove` a nivel window y actualiza dos
   *  CSS vars sobre el elemento `.portfolio-cursor-glow`. El CSS hace
   *  el resto — `radial-gradient(600px at var(--pf-mx) var(--pf-my))`.
   *
   *  Corre FUERA de la Angular zone: mutamos `.style.setProperty` que
   *  no dispara change detection, y así 60fps de mousemove no le
   *  cuestan nada al framework. Skip en touch (no hay mouse). */
  private attachCursorGlow(): void {
    if (typeof window === 'undefined') return;
    if (!window.matchMedia('(hover: hover) and (pointer: fine)').matches) return;

    this.zone.runOutsideAngular(() => {
      this.mouseMoveHandler = (e: MouseEvent) => {
        const el = this.cursorGlow()?.nativeElement;
        if (!el) return;
        el.style.setProperty('--pf-mx', `${e.clientX}px`);
        el.style.setProperty('--pf-my', `${e.clientY}px`);
      };
      window.addEventListener('mousemove', this.mouseMoveHandler, { passive: true });
    });
  }
}

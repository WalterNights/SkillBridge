import {
  AfterViewInit,
  Component,
  OnDestroy,
  inject,
  signal,
} from '@angular/core';

import { PortfolioI18nService } from '../i18n/portfolio-i18n.service';

interface NavItem {
  id: 'about' | 'experience' | 'projects' | 'contact';
  labelKey: string;
}

/**
 * Sidebar sticky del portafolio.
 *
 * Estructura: identidad (nombre + rol + tagline) arriba, nav-anchor al
 * medio con la línea que crece al item activo (estilo Brittany Chiang),
 * socials + toggle de idioma abajo.
 *
 * El item activo se detecta con IntersectionObserver sobre las <section>
 * del <main> — cuando el centro del viewport toca una sección, ese item
 * enciende la línea. No usamos scroll listener (mucho más caro).
 */
@Component({
  selector: 'app-portfolio-sidebar',
  standalone: true,
  imports: [],
  templateUrl: './sidebar.component.html',
  styleUrl: './sidebar.component.scss',
})
export class PortfolioSidebarComponent implements AfterViewInit, OnDestroy {
  readonly i18n = inject(PortfolioI18nService);

  readonly nav: readonly NavItem[] = [
    { id: 'about', labelKey: 'sidebar.nav.about' },
    { id: 'experience', labelKey: 'sidebar.nav.experience' },
    { id: 'projects', labelKey: 'sidebar.nav.projects' },
    { id: 'contact', labelKey: 'sidebar.nav.contact' },
  ];

  readonly activeId = signal<NavItem['id']>('about');

  private observer?: IntersectionObserver;

  ngAfterViewInit(): void {
    const sections = this.nav
      .map((n) => document.getElementById(n.id))
      .filter((el): el is HTMLElement => el !== null);

    if (sections.length === 0) return;

    // rootMargin: activa cuando la sección está en el tercio central del
    // viewport. Threshold escalonado da mejor granularidad para elegir
    // la sección con mayor visibilidad cuando dos están en pantalla.
    this.observer = new IntersectionObserver(
      (entries) => {
        const visible = entries
          .filter((e) => e.isIntersecting)
          .sort((a, b) => b.intersectionRatio - a.intersectionRatio)[0];
        if (visible) {
          this.activeId.set(visible.target.id as NavItem['id']);
        }
      },
      { rootMargin: '-40% 0px -55% 0px', threshold: [0, 0.25, 0.5, 0.75, 1] },
    );

    sections.forEach((s) => this.observer!.observe(s));
  }

  ngOnDestroy(): void {
    this.observer?.disconnect();
  }

  onNavClick(event: Event, id: NavItem['id']): void {
    event.preventDefault();
    document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    this.activeId.set(id);
  }

  setLang(lang: 'es' | 'en'): void {
    this.i18n.setLang(lang);
  }
}

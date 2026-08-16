import {
  AfterViewInit,
  Component,
  OnDestroy,
  computed,
  inject,
  signal,
} from '@angular/core';

import { PortfolioI18nService } from '../i18n/portfolio-i18n.service';
import { findIconById } from '../data/portfolio-icons.data';
import { PortfolioIconComponent } from './portfolio-icon.component';

interface NavItem {
  id: 'about' | 'experience' | 'projects' | 'contact';
  labelKey: string;
}

interface SocialLink {
  id: string;
  url: string;
}

/**
 * Sidebar sticky del portafolio.
 *
 * Estructura: identidad → nav-anchor con línea que crece (estilo Brittany
 * Chiang) → tech chips → socials → lang toggle.
 *
 * Socials y tech vienen del JSON del backend (editable via editor).
 * Cada uno se renderiza con `<pf-icon>` a partir del catálogo curado
 * en `portfolio-icons.data.ts`. Si un id no existe en el catálogo, el
 * icono no se pinta (fail-silent) — mejor que un placeholder feo.
 *
 * La detección de sección activa usa IntersectionObserver — más barato
 * que un scroll listener y con narrow-ing automático de tipos.
 */
@Component({
  selector: 'app-portfolio-sidebar',
  standalone: true,
  imports: [PortfolioIconComponent],
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

  /** Lista de socials del JSON — array de {id, url}. Filtra los ids
   *  desconocidos por defensa (json corrupto o icono removido). */
  readonly socials = computed<SocialLink[]>(() => {
    const raw = this.i18n.raw<SocialLink[]>('sidebar.socials');
    if (!Array.isArray(raw)) return [];
    return raw.filter(
      (link) => link && typeof link.id === 'string' && typeof link.url === 'string' && link.url,
    );
  });

  /** Stack tech — array de icon ids. Filtra unknowns. */
  readonly tech = computed<{ id: string; name: string }[]>(() => {
    const raw = this.i18n.raw<string[]>('sidebar.tech');
    if (!Array.isArray(raw)) return [];
    return raw
      .map((id) => {
        const def = findIconById(id);
        return def ? { id, name: def.name } : null;
      })
      .filter((x): x is { id: string; name: string } => x !== null);
  });

  socialName(id: string): string {
    return findIconById(id)?.name ?? id;
  }

  /** URL final del social. Para WhatsApp normaliza inputs parciales:
   *  `@nickname` o número puro → prefija con `https://wa.me/`.
   *  wa.me redirige a WhatsApp Web en desktop y a la app en mobile,
   *  así que un solo formato sirve para ambos. Para el resto de socials
   *  devuelve el URL tal cual (asume que el user tipeó una URL completa). */
  resolvedUrl(link: SocialLink): string {
    const raw = (link.url ?? '').trim();
    if (!raw) return '';
    if (/^(https?:|mailto:|tel:)/i.test(raw)) return raw;

    if (link.id === 'whatsapp') {
      // Numero puro (con opcional +) → wa.me/numero (sin +).
      const digitsOnly = raw.replace(/[\s\-()]/g, '');
      if (/^\+?\d{7,}$/.test(digitsOnly)) {
        return `https://wa.me/${digitsOnly.replace(/^\+/, '')}`;
      }
      // Nickname (con o sin @) → wa.me/@user (Meta nickname format).
      const nick = raw.startsWith('@') ? raw : `@${raw}`;
      return `https://wa.me/${nick}`;
    }

    // Default: dejamos como esta — responsabilidad del user tipearlo bien.
    return raw;
  }

  /** Label del tooltip. Por default el nombre humano del icono
   *  ("GitHub", "LinkedIn"). Para WhatsApp muestra el nickname o número
   *  extraído del URL — mas util al hacer hover que un generico "WhatsApp". */
  tooltipLabel(link: SocialLink): string {
    if (link.id === 'whatsapp') {
      const raw = (link.url ?? '').trim();
      if (!raw) return this.socialName(link.id);
      // Extrae la parte identificatoria despues de wa.me/ o web.whatsapp.com/
      const stripped = raw
        .replace(/^https?:\/\/(www\.)?wa\.me\//i, '')
        .replace(/^https?:\/\/(www\.)?web\.whatsapp\.com\/send\?phone=/i, '')
        .replace(/^https?:\/\/(www\.)?api\.whatsapp\.com\/send\?phone=/i, '');
      return stripped || this.socialName(link.id);
    }
    return this.socialName(link.id);
  }

  private observer?: IntersectionObserver;

  ngAfterViewInit(): void {
    const sections = this.nav
      .map((n) => document.getElementById(n.id))
      .filter((el): el is HTMLElement => el !== null);

    if (sections.length === 0) return;

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

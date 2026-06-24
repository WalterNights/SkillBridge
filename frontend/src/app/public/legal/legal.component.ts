import { CommonModule, Location } from '@angular/common';
import { Component, computed, inject, signal } from '@angular/core';
import { Title, Meta } from '@angular/platform-browser';
import { ActivatedRoute, RouterLink } from '@angular/router';

import { PublicFooterComponent } from '../../shared/public-footer/public-footer.component';
import { PublicNavComponent } from '../../shared/public-nav/public-nav.component';
import { LegalDoc, findLegalBySlug } from './legal-data';

/**
 * Vista compartida para las páginas legales — /legal/:slug.
 *
 * Lookup del documento en el catálogo estático en legal-data.ts:
 *   /legal/privacidad → Política de Privacidad
 *   /legal/terminos   → Términos y Condiciones
 *   /legal/cookies    → Política de Cookies
 *
 * Si el slug no existe, render del 404 inline. Mismo pattern que
 * /recursos/:slug — consistencia visual y código.
 */
@Component({
  selector: 'app-legal',
  standalone: true,
  imports: [CommonModule, RouterLink, PublicNavComponent, PublicFooterComponent],
  templateUrl: './legal.component.html',
  styleUrl: './legal.component.scss',
})
export class LegalComponent {
  doc = signal<LegalDoc | undefined>(undefined);

  /** Para el índice lateral (anchor links). */
  toc = computed(() => this.doc()?.sections ?? []);

  private route = inject(ActivatedRoute);
  private location = inject(Location);
  private titleService = inject(Title);
  private meta = inject(Meta);

  constructor() {
    this.route.paramMap.subscribe((params) => {
      const slug = params.get('slug') ?? '';
      const found = findLegalBySlug(slug);
      this.doc.set(found);
      if (found) {
        this.titleService.setTitle(`${found.title} | SkilTak`);
        this.meta.updateTag({ name: 'description', content: found.excerpt });
      } else {
        this.titleService.setTitle('Documento legal no encontrado | SkilTak');
      }
      window.scrollTo({ top: 0, behavior: 'instant' });
    });
  }

  goBack(): void {
    this.location.back();
  }
}

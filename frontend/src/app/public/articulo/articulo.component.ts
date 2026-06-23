import { CommonModule, Location } from '@angular/common';
import { Component, inject, signal } from '@angular/core';
import { Title } from '@angular/platform-browser';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';

import { PublicFooterComponent } from '../../shared/public-footer/public-footer.component';
import { PublicNavComponent } from '../../shared/public-nav/public-nav.component';
import { Article, ARTICLES, findArticleBySlug } from '../recursos/articles-data';

/**
 * Vista de artículo individual /recursos/:slug.
 *
 * Lookup del artículo en el catálogo estático en articles-data.ts.
 * Si el slug no existe, render del 404 inline (no redirige) para que
 * el user pueda navegar de vuelta sin perder contexto del breadcrumb.
 */
@Component({
  selector: 'app-articulo',
  standalone: true,
  imports: [CommonModule, RouterLink, PublicNavComponent, PublicFooterComponent],
  templateUrl: './articulo.component.html',
  styleUrl: './articulo.component.scss',
})
export class ArticuloComponent {
  article = signal<Article | undefined>(undefined);

  /** Artículos sugeridos al final — todos menos el actual. */
  related = signal<Article[]>([]);

  private route = inject(ActivatedRoute);
  private location = inject(Location);
  private router = inject(Router);
  private titleService = inject(Title);

  constructor() {
    // ParamMap es Observable — nos suscribimos para soportar nav entre
    // /recursos/A → /recursos/B sin destruir el componente.
    this.route.paramMap.subscribe((params) => {
      const slug = params.get('slug') ?? '';
      const found = findArticleBySlug(slug);
      this.article.set(found);
      if (found) {
        this.titleService.setTitle(`${found.title} | SkilTak`);
        this.related.set(ARTICLES.filter((a) => a.slug !== found.slug).slice(0, 2));
      } else {
        this.titleService.setTitle('Artículo no encontrado | SkilTak');
      }
      window.scrollTo({ top: 0, behavior: 'instant' });
    });
  }

  goBack(): void {
    this.location.back();
  }
}

import { CommonModule } from '@angular/common';
import { Component } from '@angular/core';
import { Title } from '@angular/platform-browser';
import { RouterLink } from '@angular/router';

import { PublicFooterComponent } from '../../shared/public-footer/public-footer.component';
import { PublicNavComponent } from '../../shared/public-nav/public-nav.component';
import { ARTICLES } from './articles-data';

/**
 * Index de /recursos — grilla de cards con todos los artículos
 * disponibles. La fuente es el array estático en articles-data.ts.
 *
 * Cuando crezcan los artículos (~15+), agregamos filtro por categoría
 * arriba de la grilla. Por ahora la lista cabe sin filtro.
 */
@Component({
  selector: 'app-recursos',
  standalone: true,
  imports: [CommonModule, RouterLink, PublicNavComponent, PublicFooterComponent],
  templateUrl: './recursos.component.html',
  styleUrl: './recursos.component.scss',
})
export class RecursosComponent {
  articles = ARTICLES;

  constructor(title: Title) {
    title.setTitle('Recursos — Guías de carrera para Latam | SkilTak');
  }
}

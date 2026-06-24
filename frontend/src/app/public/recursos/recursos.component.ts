import { CommonModule } from '@angular/common';
import { Component, inject } from '@angular/core';
import { Title } from '@angular/platform-browser';
import { RouterLink } from '@angular/router';

import { AuthService } from '../../auth/auth.service';
import { PublicFooterComponent } from '../../shared/public-footer/public-footer.component';
import { PublicNavComponent } from '../../shared/public-nav/public-nav.component';
import { ARTICLES } from './articles-data';

/**
 * Index de /recursos — grilla de cards con todos los artículos
 * disponibles. La fuente es el array estático en articles-data.ts.
 *
 * UI adapt: si el user está autenticado, este componente se renderea
 * DENTRO del AppShell (route con canMatch=authMatchGuard), entonces no
 * dibujamos PublicNav ni PublicFooter — el chrome lo provee el shell.
 * Si no está autenticado, cae al route público y rendereamos chrome
 * propio.
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
  /** True cuando el componente vive dentro del AppShell (auth user).
   * El template usa esta señal para no duplicar el chrome del shell. */
  readonly insideShell: boolean;

  constructor(title: Title) {
    title.setTitle('Recursos — Guías de carrera para Latam | SkilTak');
    this.insideShell = inject(AuthService).isAuthenticated();
  }
}

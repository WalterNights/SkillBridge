import { Component, inject } from '@angular/core';
import { Title } from '@angular/platform-browser';
import { Router } from '@angular/router';

import { AuthService } from '../../auth/auth.service';
import { PublicFooterComponent } from '../../shared/public-footer/public-footer.component';
import { PublicNavComponent } from '../../shared/public-nav/public-nav.component';

/**
 * Página pública /como-funciona — explicación larga del producto.
 *
 * Profession-agnostic. 5 secciones (problema, matching, privacidad,
 * roadmap, CTA). El navbar trae anchor a `#algoritmo` desde el bloque
 * "Curaduría con IA" del home — Angular Router lleva al scroll position
 * automático cuando se pasa el `fragment`.
 */
@Component({
  selector: 'app-como-funciona',
  standalone: true,
  imports: [PublicNavComponent, PublicFooterComponent],
  templateUrl: './como-funciona.component.html',
  styleUrl: './como-funciona.component.scss',
})
export class ComoFuncionaComponent {
  private auth = inject(AuthService);
  private router = inject(Router);

  constructor(title: Title) {
    title.setTitle('Cómo funciona SkilTak — IA que centraliza ofertas');
  }

  startCta(): void {
    if (this.auth.isAuthenticated()) {
      this.router.navigate(['/dashboard']);
    } else {
      this.router.navigate(['/auth/register']);
    }
  }
}

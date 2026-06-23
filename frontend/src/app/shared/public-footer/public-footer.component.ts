import { Component } from '@angular/core';
import { RouterLink } from '@angular/router';

/**
 * Footer reusable para todas las páginas públicas (home,
 * /como-funciona, /recursos, /recursos/:slug). El año se hardcodea
 * intencionalmente — actualizarlo es trivial y evita un `new Date()`
 * en cada render del footer.
 */
@Component({
  selector: 'app-public-footer',
  standalone: true,
  imports: [RouterLink],
  templateUrl: './public-footer.component.html',
})
export class PublicFooterComponent {}

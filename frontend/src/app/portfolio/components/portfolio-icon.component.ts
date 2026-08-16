import { Component, computed, input } from '@angular/core';

import { findIconById } from '../data/portfolio-icons.data';

/**
 * Renderiza un icono del catálogo por ID. Usado por el sidebar (socials
 * + tech chips), el editor (previews de dropdown/autocomplete) y donde
 * sea que necesitemos mostrar un icono de marca.
 *
 * Si el ID no existe en el catálogo, no renderiza nada (falla silenciosa
 * — mejor que un placeholder feo). El editor previene que el user
 * seleccione un ID inválido, así que este caso solo pasaría con data
 * corrupta manual.
 */
@Component({
  selector: 'pf-icon',
  standalone: true,
  imports: [],
  template: `
    @if (def(); as icon) {
      <svg
        [attr.viewBox]="'0 0 24 24'"
        [attr.width]="size()"
        [attr.height]="size()"
        [attr.aria-label]="icon.name"
        role="img"
        focusable="false"
      >
        <path fill="currentColor" [attr.d]="icon.path" />
      </svg>
    }
  `,
  styles: [
    `
      :host {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        line-height: 0;
      }
    `,
  ],
})
export class PortfolioIconComponent {
  readonly id = input.required<string>();
  readonly size = input<number>(20);

  readonly def = computed(() => findIconById(this.id()));
}

import { Component, input } from '@angular/core';

/**
 * Cabecera compartida por todas las secciones del portafolio: eyebrow
 * mono en naranja + título en serif. Reduce duplicación entre About /
 * Experience / Projects / Contact.
 */
@Component({
  selector: 'app-pf-section-header',
  standalone: true,
  imports: [],
  template: `
    <header class="pf-sh">
      <p class="pf-sh__eyebrow">
        <span class="pf-sh__slash" aria-hidden="true">/</span>
        {{ eyebrow() }}
      </p>
      <h2 class="pf-sh__title">{{ title() }}</h2>
    </header>
  `,
  styles: [
    `
      :host {
        display: block;
        margin-bottom: 48px;
      }

      .pf-sh {
        &__eyebrow {
          display: inline-flex;
          align-items: center;
          gap: 12px;
          margin: 0 0 20px;
          font-family: var(--pf-font-mono);
          font-size: 12px;
          letter-spacing: 0.14em;
          color: var(--pf-accent);
        }

        &__slash {
          color: var(--pf-text-mute);
        }

        &__title {
          margin: 0;
          font-family: var(--pf-font-display);
          font-weight: 900;
          font-size: clamp(36px, 5vw, 56px);
          line-height: 1.05;
          letter-spacing: -0.03em;
          color: var(--pf-text);
        }
      }
    `,
  ],
})
export class PfSectionHeaderComponent {
  readonly eyebrow = input.required<string>();
  readonly title = input.required<string>();
}

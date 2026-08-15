import { Component, inject } from '@angular/core';

import { PortfolioI18nService } from '../i18n/portfolio-i18n.service';

@Component({
  selector: 'app-hero-section',
  standalone: true,
  imports: [],
  templateUrl: './hero.component.html',
  styleUrl: './hero.component.scss',
})
export class HeroSectionComponent {
  readonly i18n = inject(PortfolioI18nService);

  scrollTo(id: string, event: Event): void {
    event.preventDefault();
    document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }
}

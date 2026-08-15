import { Component, inject } from '@angular/core';

import { PortfolioI18nService } from '../i18n/portfolio-i18n.service';
import { PfSectionHeaderComponent } from './section-header.component';

@Component({
  selector: 'app-about-section',
  standalone: true,
  imports: [PfSectionHeaderComponent],
  templateUrl: './about.component.html',
  styleUrl: './about.component.scss',
})
export class AboutSectionComponent {
  readonly i18n = inject(PortfolioI18nService);

  get paragraphs(): string[] {
    return this.i18n.raw<string[]>('about.paragraphs') ?? [];
  }
}

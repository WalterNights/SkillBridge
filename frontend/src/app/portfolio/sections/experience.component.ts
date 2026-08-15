import { Component, computed, inject } from '@angular/core';

import { PortfolioI18nService } from '../i18n/portfolio-i18n.service';
import { PfSectionHeaderComponent } from './section-header.component';

interface ExperienceItem {
  period: string;
  role: string;
  company: string;
  url?: string;
  description: string;
  stack: string[];
}

@Component({
  selector: 'app-experience-section',
  standalone: true,
  imports: [PfSectionHeaderComponent],
  templateUrl: './experience.component.html',
  styleUrl: './experience.component.scss',
})
export class ExperienceSectionComponent {
  readonly i18n = inject(PortfolioI18nService);

  readonly items = computed<ExperienceItem[]>(
    () => this.i18n.raw<ExperienceItem[]>('experience.items') ?? [],
  );
}

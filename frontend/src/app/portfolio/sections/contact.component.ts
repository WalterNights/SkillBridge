import { Component, inject } from '@angular/core';

import { PortfolioI18nService } from '../i18n/portfolio-i18n.service';
import { PfSectionHeaderComponent } from './section-header.component';

@Component({
  selector: 'app-contact-section',
  standalone: true,
  imports: [PfSectionHeaderComponent],
  templateUrl: './contact.component.html',
  styleUrl: './contact.component.scss',
})
export class ContactSectionComponent {
  readonly i18n = inject(PortfolioI18nService);
}

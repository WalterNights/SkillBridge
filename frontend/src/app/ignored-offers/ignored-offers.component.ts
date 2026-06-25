import { CommonModule } from '@angular/common';
import { HttpErrorResponse } from '@angular/common/http';
import { Component, signal } from '@angular/core';
import { Router, RouterModule } from '@angular/router';
import { Title } from '@angular/platform-browser';

import { JobOffer } from '../models/job-offer.model';
import { JobService } from '../services/job.service';
import { ToastService } from '../services/toast.service';
import { portalMeta } from '../shared/portal';

/**
 * Vista de ofertas que el user marcó como "Ignorar" desde el feed.
 *
 * Usa el mismo lenguaje visual que /dashboard (cards glass) pero con:
 *   - Botón "Restaurar" (un-ignore) en vez de "Ignorar"
 *   - Empty state distinto: "Tu lista de ignoradas está vacía"
 *
 * El backend purga las ofertas viejas (>30d) via cron `clean_old_offers`
 * y el CASCADE de IgnoredOffer.offer las saca de esta lista también — no
 * hay cleanup adicional acá.
 */
@Component({
  selector: 'app-ignored-offers',
  standalone: true,
  imports: [CommonModule, RouterModule],
  templateUrl: './ignored-offers.component.html',
  styleUrls: ['./ignored-offers.component.scss'],
})
export class IgnoredOffersComponent {
  offers = signal<JobOffer[]>([]);
  isLoading = signal<boolean>(true);

  constructor(
    private jobService: JobService,
    private router: Router,
    private toast: ToastService,
    private titleService: Title,
  ) {
    this.titleService.setTitle('SkilTak — Ofertas ignoradas');
  }

  ngOnInit(): void {
    this.load();
  }

  private load(): void {
    this.isLoading.set(true);
    this.jobService.getIgnoredOffers().subscribe({
      next: (data) => {
        this.offers.set(data);
        this.isLoading.set(false);
      },
      error: (err: HttpErrorResponse) => {
        console.error('Failed to load ignored offers:', err);
        this.offers.set([]);
        this.isLoading.set(false);
      },
    });
  }

  /** Quita el ignore — optimista: removemos de la lista y rollback si falla. */
  restore(offer: JobOffer): void {
    const original = this.offers();
    this.offers.set(original.filter((o) => o.id !== offer.id));
    this.jobService.unignoreOffer(offer.id).subscribe({
      next: () => this.toast.success('Oferta restaurada — vuelve a aparecer en tu feed.'),
      error: () => {
        this.offers.set(original);
        this.toast.error('No pudimos restaurar la oferta. Intentá de nuevo.');
      },
    });
  }

  goToDetail(offer: JobOffer): void {
    this.jobService.setSelectedJob(offer);
    this.router.navigate(['/jobs', offer.id]);
  }

  portalMeta(offer: JobOffer) {
    return portalMeta(offer);
  }

  trackOffer(_index: number, offer: JobOffer): number {
    return offer.id;
  }
}

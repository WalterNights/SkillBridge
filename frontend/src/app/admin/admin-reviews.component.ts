import { CommonModule } from '@angular/common';
import { HttpErrorResponse } from '@angular/common/http';
import { Component, OnInit, inject, signal } from '@angular/core';
import { Title } from '@angular/platform-browser';

import { AdminReview, ReviewService, ReviewStatus } from '../services/review.service';
import { ToastService } from '../services/toast.service';

type Filter = ReviewStatus | 'all';

const FILTERS: readonly { key: Filter; label: string }[] = [
  { key: 'pending', label: 'Pendientes' },
  { key: 'published', label: 'Publicadas' },
  { key: 'rejected', label: 'Rechazadas' },
  { key: 'all', label: 'Todas' },
];

/**
 * Panel admin /admin/reviews — cola de moderación de reseñas.
 *
 * El admin solo publica o rechaza: no puede editar el texto ni la
 * calificación del usuario (read-only en el backend). Una reseña
 * publicada llega al landing solo si además tiene 4-5 estrellas y el
 * usuario dio consentimiento — el backend lo calcula en `landing_eligible`.
 */
@Component({
  selector: 'app-admin-reviews',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './admin-reviews.component.html',
})
export class AdminReviewsComponent implements OnInit {
  private reviewService = inject(ReviewService);
  private toast = inject(ToastService);

  readonly filters = FILTERS;
  readonly stars = [1, 2, 3, 4, 5];

  filter = signal<Filter>('pending');
  reviews = signal<AdminReview[]>([]);
  total = signal(0);
  isLoading = signal(true);
  errorMessage = signal('');
  savingId = signal<number | null>(null);

  constructor(title: Title) {
    title.setTitle('SkilTak — Admin · Reseñas');
  }

  ngOnInit(): void {
    this.load();
  }

  setFilter(key: Filter): void {
    this.filter.set(key);
    this.load();
  }

  private load(): void {
    this.isLoading.set(true);
    this.errorMessage.set('');
    this.reviewService.adminList(this.filter()).subscribe({
      next: (page) => {
        this.reviews.set(page.results);
        this.total.set(page.count);
        this.isLoading.set(false);
      },
      error: (err: HttpErrorResponse) => {
        this.errorMessage.set(
          err.status === 403
            ? 'No tienes permisos para ver esta sección.'
            : 'No pudimos cargar las reseñas.',
        );
        this.isLoading.set(false);
      },
    });
  }

  publish(r: AdminReview): void {
    this.moderate(r, 'published');
  }

  reject(r: AdminReview): void {
    const note = prompt('Motivo del rechazo (opcional, lo ve el usuario):', '');
    if (note === null) return;
    this.moderate(r, 'rejected', note.trim());
  }

  private moderate(r: AdminReview, status: ReviewStatus, note = ''): void {
    this.savingId.set(r.id);
    this.reviewService.adminUpdate(r.id, { status, moderation_note: note }).subscribe({
      next: (updated) => {
        this.savingId.set(null);
        // Si el filtro actual ya no incluye el nuevo estado, sale de la lista.
        const keep = this.filter() === 'all' || this.filter() === updated.status;
        this.reviews.update((list) =>
          keep
            ? list.map((x) => (x.id === updated.id ? updated : x))
            : list.filter((x) => x.id !== updated.id),
        );
        if (!keep) this.total.update((n) => n - 1);
        this.toast.success(status === 'published' ? 'Reseña publicada' : 'Reseña rechazada');
      },
      error: () => {
        this.savingId.set(null);
        this.toast.error('No pudimos actualizar la reseña.');
      },
    });
  }

  formatDate(iso: string): string {
    return new Date(iso).toLocaleString('es', { dateStyle: 'medium', timeStyle: 'short' });
  }
}

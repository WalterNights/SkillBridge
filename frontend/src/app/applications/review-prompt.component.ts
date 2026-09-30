import { CommonModule } from '@angular/common';
import { HttpErrorResponse } from '@angular/common/http';
import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';

import { MyReviewState, ReviewService, ReviewStatus } from '../services/review.service';
import { ToastService } from '../services/toast.service';

const COMMENT_MIN = 20;
const COMMENT_MAX = 500;

const STATUS_LABEL: Record<ReviewStatus, string> = {
  pending: 'En revisión',
  published: 'Publicada',
  rejected: 'No publicada',
};

/**
 * Tarjeta de reseña en /applications.
 *
 * Tres estados según `/api/reviews/me/`:
 *   - No elegible → progreso "N de M postulaciones confirmadas".
 *   - Elegible sin reseña (o editando) → formulario.
 *   - Con reseña → resumen + estado de moderación + editar/borrar.
 *
 * El gating real lo hace el backend (403 si no llega al mínimo); acá
 * solo decidimos qué mostrar.
 */
@Component({
  selector: 'app-review-prompt',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './review-prompt.component.html',
})
export class ReviewPromptComponent implements OnInit {
  private reviews = inject(ReviewService);
  private toast = inject(ToastService);

  readonly stars = [1, 2, 3, 4, 5];
  readonly commentMin = COMMENT_MIN;
  readonly commentMax = COMMENT_MAX;
  // Material Symbols: estrella rellena vs contorno.
  readonly fillOn = "'FILL' 1";
  readonly fillOff = "'FILL' 0";

  state = signal<MyReviewState | null>(null);
  editing = signal(false);
  saving = signal(false);

  // Form
  rating = signal(0);
  comment = signal('');
  // Opt-in: el consentimiento para mostrar nombre y foto debe ser explícito.
  allowPublic = signal(false);

  progressPct = computed(() => {
    const s = this.state();
    if (!s || s.min_applications === 0) return 0;
    return Math.min(100, Math.round((s.applications_count / s.min_applications) * 100));
  });

  canSubmit = computed(() => {
    const len = this.comment().trim().length;
    return this.rating() > 0 && len >= COMMENT_MIN && len <= COMMENT_MAX && !this.saving();
  });

  showForm = computed(() => {
    const s = this.state();
    return !!s && s.eligible && (!s.review || this.editing());
  });

  ngOnInit(): void {
    this.reviews.getMine().subscribe({
      next: (s) => this.state.set(s),
      // Sin estado no mostramos la tarjeta — no es crítico para la página.
      error: () => this.state.set(null),
    });
  }

  statusLabel(status: ReviewStatus): string {
    return STATUS_LABEL[status];
  }

  startEdit(): void {
    const review = this.state()?.review;
    if (review) {
      this.rating.set(review.rating);
      this.comment.set(review.comment);
      this.allowPublic.set(review.allow_public);
    }
    this.editing.set(true);
  }

  cancelEdit(): void {
    this.editing.set(false);
  }

  submit(): void {
    if (!this.canSubmit()) return;
    this.saving.set(true);
    this.reviews
      .saveMine({
        rating: this.rating(),
        comment: this.comment().trim(),
        allow_public: this.allowPublic(),
      })
      .subscribe({
        next: (s) => {
          this.state.set(s);
          this.editing.set(false);
          this.saving.set(false);
          this.toast.success('¡Gracias! Tu reseña quedó en revisión.');
        },
        error: (err: HttpErrorResponse) => {
          this.saving.set(false);
          const detail =
            err.error?.detail ?? err.error?.comment?.[0] ?? 'No pudimos guardar tu reseña.';
          this.toast.error(detail);
        },
      });
  }

  remove(): void {
    if (!confirm('¿Borrar tu reseña?')) return;
    this.reviews.deleteMine().subscribe({
      next: () => {
        this.state.update((s) => (s ? { ...s, review: null } : s));
        this.rating.set(0);
        this.comment.set('');
        this.toast.success('Reseña borrada.');
      },
      error: () => this.toast.error('No pudimos borrar tu reseña.'),
    });
  }
}

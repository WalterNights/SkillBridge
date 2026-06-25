import { CommonModule } from '@angular/common';
import { HttpErrorResponse } from '@angular/common/http';
import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Title } from '@angular/platform-browser';

import {
  FaqAdminEntry,
  FaqAdminStats,
  FaqCategory,
  FaqService,
} from '../services/faq.service';
import { ToastService } from '../services/toast.service';

type StatusFilter = 'pending' | 'published' | 'rejected' | 'all';

/** Edit-state local de una FAQ — buffer entre el UI y el PATCH al
 *  backend. Se inicializa al expandir un card. */
interface DraftFaq {
  answer: string;
  categoryId: number | null;
  moderationNote: string;
}

/**
 * Panel admin /admin/faqs — moderación de preguntas + métricas FAQ.
 *
 * Capacidades:
 *   - Filtra por estado (pending por default).
 *   - Cada card: pregunta, draft AI, textarea para editar respuesta,
 *     selector de categoría, botones Publicar/Rechazar/Eliminar.
 *   - Stats cards arriba (total, pending, ratio aprobación).
 *
 * El backend hace doble-gating (IsAdminUser); el frontend usa
 * AdminGuard del router como UX-gate.
 */
@Component({
  selector: 'app-admin-faqs',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './admin-faqs.component.html',
  styleUrls: ['./admin-faqs.component.scss'],
})
export class AdminFaqsComponent implements OnInit {
  private faqService = inject(FaqService);
  private toast = inject(ToastService);

  faqs = signal<FaqAdminEntry[]>([]);
  categories = signal<FaqCategory[]>([]);
  stats = signal<FaqAdminStats | null>(null);

  isLoading = signal(true);
  errorMessage = signal('');
  statusFilter = signal<StatusFilter>('pending');

  /** Map id → draft cuando el card está en edición. */
  drafts = signal<Map<number, DraftFaq>>(new Map());
  /** Estado "guardando" por id, para deshabilitar botones por card. */
  saving = signal<Set<number>>(new Set());

  filterOptions: { value: StatusFilter; label: string }[] = [
    { value: 'pending', label: 'Pendientes' },
    { value: 'published', label: 'Publicadas' },
    { value: 'rejected', label: 'Rechazadas' },
    { value: 'all', label: 'Todas' },
  ];

  totalShown = computed(() => this.faqs().length);

  constructor(title: Title) {
    title.setTitle('SkilTak — Admin · FAQ');
  }

  ngOnInit(): void {
    this.faqService.listCategories().subscribe({
      next: (cats) => this.categories.set(cats),
    });
    this.loadFaqs();
    this.loadStats();
  }

  private loadFaqs(): void {
    this.isLoading.set(true);
    this.faqService.adminList(this.statusFilter()).subscribe({
      next: (res) => {
        this.faqs.set(res.results);
        this.drafts.set(new Map());
        this.isLoading.set(false);
      },
      error: (err: HttpErrorResponse) => {
        this.errorMessage.set(
          err.status === 403
            ? 'No tienes permisos para ver esta sección.'
            : 'Error al cargar las preguntas.',
        );
        this.isLoading.set(false);
      },
    });
  }

  private loadStats(): void {
    this.faqService.adminStats().subscribe({
      next: (data) => this.stats.set(data),
      error: () => {
        /* Soft-fail: las cards arriba quedan en 0; lista funciona igual. */
      },
    });
  }

  setFilter(value: StatusFilter): void {
    this.statusFilter.set(value);
    this.loadFaqs();
  }

  startEdit(faq: FaqAdminEntry): void {
    const map = new Map(this.drafts());
    map.set(faq.id, {
      answer: faq.answer || faq.ai_draft || '',
      categoryId: faq.category?.id ?? null,
      moderationNote: faq.moderation_note || '',
    });
    this.drafts.set(map);
  }

  cancelEdit(id: number): void {
    const map = new Map(this.drafts());
    map.delete(id);
    this.drafts.set(map);
  }

  isEditing(id: number): boolean {
    return this.drafts().has(id);
  }

  draftFor(id: number): DraftFaq | undefined {
    return this.drafts().get(id);
  }

  updateDraft(id: number, patch: Partial<DraftFaq>): void {
    const map = new Map(this.drafts());
    const existing = map.get(id);
    if (!existing) return;
    map.set(id, { ...existing, ...patch });
    this.drafts.set(map);
  }

  isSaving(id: number): boolean {
    return this.saving().has(id);
  }

  private markSaving(id: number, on: boolean): void {
    const set = new Set(this.saving());
    if (on) set.add(id);
    else set.delete(id);
    this.saving.set(set);
  }

  /** Publica la FAQ con (opcionalmente) cambios pendientes del draft. */
  publish(faq: FaqAdminEntry): void {
    const draft = this.drafts().get(faq.id);
    const payload = {
      status: 'published' as const,
      ...(draft
        ? {
            answer: draft.answer,
            category_id: draft.categoryId,
          }
        : {}),
    };
    if (!payload.answer && !faq.answer && !faq.ai_draft) {
      this.toast.warning('No puedes publicar una FAQ sin respuesta.');
      return;
    }
    if (!('answer' in payload) && !faq.answer) {
      // Si no había draft abierto y la entry está vacía (ai falló),
      // exigimos editar primero.
      this.toast.warning('Edita la respuesta antes de publicar.');
      return;
    }
    this.applyPatch(faq.id, payload, 'Publicada.');
  }

  reject(faq: FaqAdminEntry): void {
    const draft = this.drafts().get(faq.id);
    const note = draft?.moderationNote ?? '';
    this.applyPatch(
      faq.id,
      { status: 'rejected', moderation_note: note },
      'Rechazada.',
    );
  }

  saveDraftOnly(faq: FaqAdminEntry): void {
    const draft = this.drafts().get(faq.id);
    if (!draft) return;
    this.applyPatch(
      faq.id,
      { answer: draft.answer, category_id: draft.categoryId },
      'Cambios guardados.',
    );
  }

  hardDelete(faq: FaqAdminEntry): void {
    if (!confirm(`¿Eliminar definitivamente la pregunta "${faq.question}"? Esta acción es irreversible.`)) {
      return;
    }
    this.markSaving(faq.id, true);
    this.faqService.adminDelete(faq.id).subscribe({
      next: () => {
        this.faqs.update((rows) => rows.filter((r) => r.id !== faq.id));
        this.cancelEdit(faq.id);
        this.markSaving(faq.id, false);
        this.toast.success('Pregunta eliminada.');
        this.loadStats();
      },
      error: (err: HttpErrorResponse) => {
        this.markSaving(faq.id, false);
        this.toast.error(err.error?.detail ?? 'No pudimos eliminar la pregunta.');
      },
    });
  }

  private applyPatch(
    id: number,
    payload: Parameters<FaqService['adminUpdate']>[1],
    successMessage: string,
  ): void {
    this.markSaving(id, true);
    this.faqService.adminUpdate(id, payload).subscribe({
      next: (updated) => {
        this.faqs.update((rows) => {
          // Si el cambio saca a la FAQ del filtro actual, la quitamos
          // de la lista visible — evita confusión.
          const filter = this.statusFilter();
          if (filter !== 'all' && updated.status !== filter) {
            return rows.filter((r) => r.id !== id);
          }
          return rows.map((r) => (r.id === id ? updated : r));
        });
        this.cancelEdit(id);
        this.markSaving(id, false);
        this.toast.success(successMessage);
        this.loadStats();
      },
      error: (err: HttpErrorResponse) => {
        this.markSaving(id, false);
        this.toast.error(err.error?.detail ?? 'No pudimos guardar el cambio.');
      },
    });
  }

  trackFaq(_index: number, faq: FaqAdminEntry): number {
    return faq.id;
  }

  statusLabel(s: string): string {
    return s === 'pending' ? 'Pendiente' : s === 'published' ? 'Publicada' : 'Rechazada';
  }

  sourceLabel(s: string): string {
    return s === 'seed' ? 'Curada' : 'Usuario';
  }
}

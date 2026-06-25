import { CommonModule } from '@angular/common';
import { HttpErrorResponse } from '@angular/common/http';
import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Title } from '@angular/platform-browser';
import { Router } from '@angular/router';

import { AuthService } from '../../auth/auth.service';
import { AnalyticsService } from '../../services/analytics.service';
import {
  FaqAskResponse,
  FaqCategory,
  FaqEntry,
  FaqService,
} from '../../services/faq.service';
import { ToastService } from '../../services/toast.service';
import { PublicFooterComponent } from '../../shared/public-footer/public-footer.component';
import { PublicNavComponent } from '../../shared/public-nav/public-nav.component';

/**
 * Página pública /faq.
 *
 * Estructura:
 *   - Header con search inline + filtro por categoría
 *   - Lista de FAQs agrupada visualmente por categoría (collapse-uno)
 *   - CTA "¿No encontraste tu duda?" — si no hay sesión, manda a /login;
 *     si hay sesión, abre modal para enviar pregunta a moderación.
 *
 * El componente se usa sin shell (PublicNav + PublicFooter) cuando se
 * visita la URL directo. Si el user está logueado y entra desde el
 * menú lateral del dashboard, el AppShell wrapping decide ocultar nav
 * pública.
 */
@Component({
  selector: 'app-faq',
  standalone: true,
  imports: [CommonModule, FormsModule, PublicNavComponent, PublicFooterComponent],
  templateUrl: './faq.component.html',
  styleUrls: ['./faq.component.scss'],
})
export class FaqComponent implements OnInit {
  private faqService = inject(FaqService);
  private toast = inject(ToastService);
  private auth = inject(AuthService);
  private router = inject(Router);
  private analytics = inject(AnalyticsService);

  faqs = signal<FaqEntry[]>([]);
  categories = signal<FaqCategory[]>([]);
  isLoading = signal(true);
  errorMessage = signal('');

  /** Slug de categoría activa; '' = todas. */
  activeCategory = signal('');
  searchTerm = signal('');
  expanded = signal<Set<number>>(new Set());

  /** Modal "Hacer una pregunta" — solo para users logueados. */
  isAskModalOpen = signal(false);
  draftQuestion = signal('');
  isSubmittingQuestion = signal(false);
  /** Última respuesta AI recibida — se muestra después del submit. */
  lastAskResponse = signal<FaqAskResponse | null>(null);

  /** Filtro combinado categoría + texto (full-text simple en cliente). */
  filteredFaqs = computed(() => {
    const term = this.searchTerm().trim().toLowerCase();
    const cat = this.activeCategory();
    return this.faqs().filter((f) => {
      if (cat && f.category?.slug !== cat) return false;
      if (!term) return true;
      const haystack = `${f.question} ${f.answer}`.toLowerCase();
      return haystack.includes(term);
    });
  });

  /** FAQs agrupadas por categoría para render en bloques. Las que no
   *  tienen categoría asignada caen en un grupo "Otras" al final — así
   *  no se pierden cuando el admin publica sin categorizar. */
  faqsByCategory = computed(() => {
    const cats = this.categories();
    const filtered = this.filteredFaqs();
    const groups = cats
      .map((cat) => ({
        category: cat,
        entries: filtered.filter((f) => f.category?.id === cat.id),
      }))
      .filter((group) => group.entries.length > 0);

    const uncategorized = filtered.filter((f) => !f.category);
    if (uncategorized.length > 0) {
      groups.push({
        category: {
          id: -1,
          name: 'Otras preguntas',
          slug: '_uncategorized',
          description: '',
          display_order: 999,
        },
        entries: uncategorized,
      });
    }
    return groups;
  });

  get isAuthenticated(): boolean {
    return this.auth.isAuthenticated();
  }

  constructor(title: Title) {
    title.setTitle('SkilTak — Preguntas frecuentes');
  }

  ngOnInit(): void {
    this.loadAll();
  }

  private loadAll(): void {
    this.isLoading.set(true);
    this.faqService.listCategories().subscribe({
      next: (cats) => this.categories.set(cats),
    });
    this.faqService.listPublic().subscribe({
      next: (data) => {
        this.faqs.set(data);
        this.isLoading.set(false);
      },
      error: () => {
        this.errorMessage.set('No pudimos cargar las preguntas frecuentes.');
        this.isLoading.set(false);
      },
    });
  }

  setCategory(slug: string): void {
    this.activeCategory.set(slug);
  }

  toggle(id: number): void {
    const set = new Set(this.expanded());
    if (set.has(id)) {
      set.delete(id);
    } else {
      set.add(id);
      // Track view fire-and-forget — no esperamos respuesta.
      this.faqService.trackView(id).subscribe({ error: () => {} });
    }
    this.expanded.set(set);
  }

  isExpanded(id: number): boolean {
    return this.expanded().has(id);
  }

  trackFaq(_index: number, faq: FaqEntry): number {
    return faq.id;
  }

  // ─── Ask flow ──────────────────────────────────────────────────────

  openAskModal(): void {
    if (!this.isAuthenticated) {
      this.analytics.trackClick('faq_ask_login_required');
      // Redirige al login con returnUrl para volver a /faq tras autenticar.
      this.router.navigate(['/auth/login'], { queryParams: { returnUrl: '/faq' } });
      return;
    }
    this.analytics.trackClick('faq_ask_open');
    this.draftQuestion.set('');
    this.lastAskResponse.set(null);
    this.isAskModalOpen.set(true);
  }

  closeAskModal(): void {
    if (this.isSubmittingQuestion()) return;
    this.isAskModalOpen.set(false);
  }

  submitQuestion(): void {
    const text = this.draftQuestion().trim();
    if (text.length < 10) {
      this.toast.warning('Tu pregunta debe tener al menos 10 caracteres.');
      return;
    }
    if (text.length > 300) {
      this.toast.warning('Máximo 300 caracteres.');
      return;
    }
    this.isSubmittingQuestion.set(true);
    this.faqService.ask(text).subscribe({
      next: (res) => {
        this.lastAskResponse.set(res);
        this.isSubmittingQuestion.set(false);
        this.toast.success(res.detail);
      },
      error: (err: HttpErrorResponse) => {
        this.isSubmittingQuestion.set(false);
        if (err.status === 403) {
          // django-ratelimit responde 403 al pasar el cap (5/hora).
          this.toast.error(
            'Has hecho muchas preguntas en poco tiempo. Intenta de nuevo en una hora.',
            'Límite alcanzado',
          );
        } else {
          this.toast.error('No pudimos enviar tu pregunta. Intenta más tarde.');
        }
      },
    });
  }
}

import { CommonModule, Location } from '@angular/common';
import { Component, OnInit, inject, signal } from '@angular/core';
import { Title } from '@angular/platform-browser';
import { JobService } from '../services/job.service';
import { ApplicationService, JobApplicationDto } from '../services/application.service';
import { JobOffer } from '../models/job-offer.model';
import { ActivatedRoute, Router, RouterModule } from '@angular/router';
import { portalMeta } from '../shared/portal';
import { CoverLetterModalComponent } from '../cover-letter/cover-letter-modal.component';

const _RELATIVE_FMT = new Intl.RelativeTimeFormat('es', { numeric: 'auto' });

function _formatRelative(iso: string | undefined): string {
  if (!iso) return '';
  const then = new Date(iso).getTime();
  if (Number.isNaN(then)) return '';
  const diffSec = Math.round((then - Date.now()) / 1000);
  const abs = Math.abs(diffSec);
  if (abs < 60) return _RELATIVE_FMT.format(Math.round(diffSec), 'second');
  if (abs < 3600) return _RELATIVE_FMT.format(Math.round(diffSec / 60), 'minute');
  if (abs < 86400) return _RELATIVE_FMT.format(Math.round(diffSec / 3600), 'hour');
  if (abs < 2592000) return _RELATIVE_FMT.format(Math.round(diffSec / 86400), 'day');
  return _RELATIVE_FMT.format(Math.round(diffSec / 2592000), 'month');
}

/**
 * Detalle de una oferta de trabajo (/jobs/:id).
 *
 * Layout split estilo Stitch mockup:
 *   - Hero row con match circle (left) + sidebar de compatibilidad (right)
 *   - Body row con "Sobre el rol" (left) + skills faltantes (right)
 *
 * Renderiza dentro del AppShell, así que no monta header/sidebar propio.
 * Data viene de /api/jobs/{id} enriquecida con `match_percentage`,
 * `matched_skills` y `missing_skills` por el backend.
 */
@Component({
  selector: 'app-job-detail',
  imports: [CommonModule, RouterModule, CoverLetterModalComponent],
  standalone: true,
  templateUrl: './job-detail.component.html',
  styleUrls: ['./job-detail.component.scss'],
})
export class JobDetailComponent implements OnInit {
  job: JobOffer | null = null;
  isLoading = true;
  errorMessage = '';
  isBookmarked = false;
  isHidden = false;

  /** Visibilidad del modal de carta de presentación (lazy — el modal
   * solo se monta cuando se abre, así el GET de la carta existente
   * solo dispara cuando el user clickea). */
  showCoverLetter = signal(false);

  /**
   * State machine del CTA de aplicar:
   *   'idle'      → muestra el botón "Aplicar en {portal}"
   *   'asking'    → muestra "¿Aplicaste?" con [Sí] / [No]
   *   'confirmed' → muestra "Aplicación registrada" + link a Mis postulaciones
   *
   * Si la oferta ya está aplicada al cargar el detail, arrancamos en
   * 'confirmed' directo. Si está en pending (clickeó pero no respondió),
   * arrancamos en 'asking' para que termine el flow.
   */
  applyState = signal<'idle' | 'asking' | 'confirmed'>('idle');
  private applicationId: number | null = null;

  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private location = inject(Location);
  private jobService = inject(JobService);
  private applicationService = inject(ApplicationService);
  private titleService = inject(Title);

  constructor() {
    this.titleService.setTitle('SkilTak — Detalle de oferta');
  }

  ngOnInit() {
    const jobId = this.route.snapshot.paramMap.get('id');
    if (!jobId) {
      this.errorMessage = 'No se encontró el identificador de la oferta.';
      this.isLoading = false;
      return;
    }
    this.jobService.getJobDetail(jobId).subscribe({
      next: (data) => {
        this.job = data;
        this.isLoading = false;
        this.hydrateApplicationState(data.id);
      },
      error: () => {
        this.errorMessage = 'No pudimos cargar la oferta.';
        this.isLoading = false;
      },
    });
  }

  /** Si el user ya tiene un JobApplication para esta oferta, ajusta el
   * estado inicial del CTA para no re-mostrar el botón "Aplicar". */
  private hydrateApplicationState(jobId: number): void {
    this.applicationService.list().subscribe({
      next: (apps) => {
        const existing = apps.find((a) => a.offer.id === jobId);
        if (!existing) return;
        this.applicationId = existing.id;
        this.applyState.set(existing.status === 'applied' ? 'confirmed' : 'asking');
      },
      error: () => {
        /* Soft-fail: el CTA queda en 'idle' (default). */
      },
    });
  }

  /** User clickea "Aplicar en X". Abre el portal en tab nueva y
   * registra el clic como pending. La card cambia a "¿Aplicaste?". */
  onApplyClick(): void {
    if (!this.job) return;
    // Abrir el portal primero — si el POST falla por red, el flujo de
    // aplicar al portal NO se rompe (el seguimiento es secundario).
    window.open(this.job.url, '_blank', 'noopener,noreferrer');
    this.applyState.set('asking');
    this.applicationService.create(this.job.id).subscribe({
      next: (app: JobApplicationDto) => {
        this.applicationId = app.id;
        // Si la oferta ya estaba en 'applied' (clicked Apply de nuevo
        // después de confirmar), respeto ese estado.
        if (app.status === 'applied') {
          this.applyState.set('confirmed');
        }
      },
      error: () => {
        // No tira atrás el flow del user — pero perdemos tracking.
        // Logueamos a consola para diagnóstico; UX queda en 'asking'
        // pero confirmar no va a tener id, así que volvemos a 'idle'.
        console.warn('Failed to track application click');
        this.applyState.set('idle');
      },
    });
  }

  /** "Sí, aplicar" → confirm via API → estado final 'confirmed'. */
  onConfirmApplied(): void {
    if (!this.applicationId) return;
    this.applicationService.confirm(this.applicationId).subscribe({
      next: () => this.applyState.set('confirmed'),
      error: () => {
        /* Soft-fail: queda en 'asking', el user puede reintentar. */
      },
    });
  }

  /** "No, todavía no" → borra el registro y vuelve a 'idle'. */
  onCancelApplied(): void {
    if (!this.applicationId) {
      this.applyState.set('idle');
      return;
    }
    const idToDelete = this.applicationId;
    // Optimistic: vuelve a 'idle' ya, rollback si falla.
    const prevId = this.applicationId;
    this.applyState.set('idle');
    this.applicationId = null;
    this.applicationService.delete(idToDelete).subscribe({
      error: () => {
        this.applicationId = prevId;
        this.applyState.set('asking');
      },
    });
  }

  /** Atajo para "Ver mis postulaciones" desde el estado confirmed. */
  goToApplications(): void {
    this.router.navigate(['/applications']);
  }

  goBack(): void {
    this.location.back();
  }

  /** Tier visual del match — mismo mapeo que el feed para continuidad. */
  matchTier(): 'excellent' | 'good' | 'regular' | 'low' {
    const m = this.job?.match_percentage ?? 0;
    if (m >= 100) return 'excellent';
    if (m >= 70) return 'good';
    if (m >= 50) return 'regular';
    return 'low';
  }

  /** Label del "header" sobre el título — solo aparece en matches altos. */
  topLabel(): string | null {
    const m = this.job?.match_percentage ?? 0;
    if (m >= 90) return 'Top match · Tu mejor coincidencia';
    if (m >= 70) return 'Match alto · Vale la pena postular';
    return null;
  }

  /** Texto del CTA — "Aplicar en {portal}" si conocemos el portal. */
  applyLabel(): string {
    const label = this.portalMeta().label;
    if (!label || label === 'Oferta') return 'Aplicar a esta oferta';
    return `Aplicar en ${label}`;
  }

  /** Conteo X / Y para la row "Habilidades" del sidebar de compat. */
  skillsMatched(): number {
    return this.job?.matched_skills?.length ?? 0;
  }
  skillsTotal(): number {
    const m = this.job?.matched_skills?.length ?? 0;
    const x = this.job?.missing_skills?.length ?? 0;
    return m + x;
  }

  /** Modalidad heurística — detecta "remoto" en la location string. */
  modality(): string | null {
    const loc = (this.job?.location || '').toLowerCase();
    if (/\bremot/.test(loc)) return 'Remoto';
    if (/\bhibrid|\bh[ií]brid/.test(loc)) return 'Híbrido';
    if (/\bpresencial|\bon[\s-]?site/.test(loc)) return 'Presencial';
    return null;
  }

  /** Fecha relativa de publicación (aprox = fecha de scrape). */
  publishedRelative(): string {
    return _formatRelative(this.job?.created_at);
  }

  /** Lista de keywords del backend como pills (no-deduplicada). */
  keywordChips(): string[] {
    if (!this.job?.keywords) return [];
    return this.job.keywords.split(',').map((k) => k.trim()).filter(Boolean);
  }

  /** Portal de origen (LinkedIn, Elempleo, …) para el avatar + CTA copy. */
  portalMeta() {
    return portalMeta(this.job);
  }

  openCoverLetter(): void {
    this.showCoverLetter.set(true);
  }

  closeCoverLetter(): void {
    this.showCoverLetter.set(false);
  }

  toggleBookmark(): void {
    this.isBookmarked = !this.isBookmarked;
  }

  toggleHide(): void {
    this.isHidden = !this.isHidden;
  }

  share(): void {
    if (!this.job) return;
    const url = window.location.href;
    if (navigator.share) {
      navigator.share({ title: this.job.title, url }).catch(() => {});
    } else {
      navigator.clipboard?.writeText(url);
    }
  }
}

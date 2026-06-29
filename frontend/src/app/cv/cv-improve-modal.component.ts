import { CommonModule } from '@angular/common';
import {
  Component,
  EventEmitter,
  Input,
  OnInit,
  Output,
  computed,
  inject,
  signal,
} from '@angular/core';

import { CvImproveResponse, CvImproveService } from '../services/cv-improve.service';
import { ToastService } from '../services/toast.service';

type ViewMode = 'loading' | 'ready' | 'error';

/**
 * Modal "Mejorar mi CV con AI".
 *
 * Flow:
 *   1. Al abrirse llama POST /cv/improve/ → backend genera versión
 *      mejorada del CV (5-10s).
 *   2. Modal muestra resumen de cambios + previews (summary y skills
 *      reordenadas; experience deja ver el primer entry como sample).
 *   3. User: 'Aplicar al CV' → emite `applied` con el payload completo,
 *      el padre lo PATCHea y refresca.
 *
 * El backend NO modifica el profile — solo propone. Esto da al user
 * el control: ver antes de aceptar, descartar si no le gusta.
 */
@Component({
  selector: 'app-cv-improve-modal',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './cv-improve-modal.component.html',
  styleUrls: ['./cv-improve-modal.component.scss'],
})
export class CvImproveModalComponent implements OnInit {
  /** Datos actuales del perfil — usados para el preview before/after. */
  @Input({ required: true }) currentSummary = '';
  @Input({ required: true }) currentSkills = '';
  /** Primera entry de experiencia actual — sample para el preview. */
  @Input() currentSampleExperience: { position?: string; description?: string } | null = null;
  /** Array completo de experiencias originales — necesario para mostrar
   *  el diff de fechas (compara cada entry vs su contraparte mejorada).
   *  Si la prop no está seteada o es texto libre, la sección de fechas
   *  no se renderiza. */
  @Input() currentExperience: Array<{
    company?: string;
    position?: string;
    start_date?: string;
    end_date?: string;
  }> = [];

  @Output() applied = new EventEmitter<CvImproveResponse>();
  @Output() closed = new EventEmitter<void>();

  view = signal<ViewMode>('loading');
  proposal = signal<CvImproveResponse | null>(null);
  errorMsg = '';
  isApplying = false;

  /** Stats simples del cambio — mostrar al user 'qué tan distinto es'. */
  summaryDelta = computed(() => {
    const p = this.proposal();
    if (!p) return 0;
    return p.summary.length - this.currentSummary.length;
  });

  bulletsChanged = computed(() => {
    const p = this.proposal();
    if (!p?.experience?.length) return 0;
    // Conteo aproximado: número de bullets en la primera entry mejorada
    const first = p.experience[0];
    if (!first?.description) return 0;
    return first.description.split('\n').filter((l) => l.trim()).length;
  });

  private api = inject(CvImproveService);
  private toast = inject(ToastService);

  ngOnInit(): void {
    this.fetchProposal();
  }

  fetchProposal(): void {
    this.view.set('loading');
    this.errorMsg = '';
    this.api.improve().subscribe({
      next: (res) => {
        this.proposal.set(res);
        this.view.set('ready');
      },
      error: (err) => {
        const detail = err?.error?.detail || 'No pudimos generar mejoras. Intenta de nuevo.';
        this.errorMsg = detail;
        this.view.set('error');
      },
    });
  }

  apply(): void {
    const p = this.proposal();
    if (!p) return;
    this.isApplying = true;
    this.applied.emit(p);
    // El padre cierra el modal después de aplicar — no cerramos acá
    // por si el PATCH falla (queremos mantenerlo abierto para reintentar).
  }

  close(): void {
    if (this.isApplying) return;
    this.closed.emit();
  }

  /** Splittea description en bullets para preview. */
  bulletsOf(description: string | null | undefined): string[] {
    if (!description) return [];
    return description
      .split(/\r?\n/)
      .map((l) => l.trim().replace(/^[•\-*]\s*/, ''))
      .filter(Boolean);
  }

  /** Entries en las que Gemini modificó alguna fecha. Mostramos solo
   *  los cambios para no inflar el modal con info redundante (los que
   *  ya estaban bien no necesitan re-validación visual). */
  dateChanges = computed<
    Array<{
      label: string;
      beforeStart: string;
      beforeEnd: string;
      afterStart: string;
      afterEnd: string;
    }>
  >(() => {
    const p = this.proposal();
    if (!p?.experience?.length || this.currentExperience.length === 0) return [];
    const changes = [];
    for (let i = 0; i < p.experience.length && i < this.currentExperience.length; i++) {
      const orig = this.currentExperience[i];
      const next = p.experience[i];
      const startChanged = (orig.start_date ?? '') !== (next.start_date ?? '');
      const endChanged = (orig.end_date ?? '') !== (next.end_date ?? '');
      if (!startChanged && !endChanged) continue;
      changes.push({
        label:
          `${next.position || orig.position || '(rol)'} · ${next.company || orig.company || '(empresa)'}`.trim(),
        beforeStart: orig.start_date || '—',
        beforeEnd: orig.end_date || '—',
        afterStart: next.start_date || '—',
        afterEnd: next.end_date || '—',
      });
    }
    return changes;
  });
}

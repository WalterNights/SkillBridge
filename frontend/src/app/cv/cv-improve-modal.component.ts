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
        const detail = err?.error?.detail || 'No pudimos generar mejoras. Intentá de nuevo.';
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
}

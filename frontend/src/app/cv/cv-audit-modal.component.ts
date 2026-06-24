import { CommonModule } from '@angular/common';
import {
  Component,
  EventEmitter,
  OnInit,
  Output,
  inject,
  signal,
} from '@angular/core';

import { CvAuditResponse, CvAuditService } from '../services/cv-audit.service';

type ViewMode = 'loading' | 'ready' | 'error';

/**
 * Modal: "Auditá tu CV con AI".
 *
 * Llama al backend cuando se monta — el resultado se cachea en este
 * componente para que la regeneración requiera click explícito (no
 * cuesta tokens cada vez que el user cierra y reabre).
 *
 * El padre solo se preocupa de mount/unmount via *ngIf.
 */
@Component({
  selector: 'app-cv-audit-modal',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './cv-audit-modal.component.html',
  styleUrls: ['./cv-audit-modal.component.scss'],
})
export class CvAuditModalComponent implements OnInit {
  @Output() closed = new EventEmitter<void>();

  view = signal<ViewMode>('loading');
  result = signal<CvAuditResponse | null>(null);
  errorMsg = '';

  private api = inject(CvAuditService);

  ngOnInit(): void {
    this.fetchAudit();
  }

  fetchAudit(): void {
    this.view.set('loading');
    this.errorMsg = '';
    this.api.audit().subscribe({
      next: (res) => {
        this.result.set(res);
        this.view.set('ready');
      },
      error: (err) => {
        const detail = err?.error?.detail || 'No pudimos analizar tu CV. Intentá de nuevo.';
        this.errorMsg = detail;
        this.view.set('error');
      },
    });
  }

  /** Tier visual del score — sirve para colorear el gauge.
   * 80+ = excelente, 60-79 = bueno, <60 = mejorable. */
  scoreTier(): 'excellent' | 'good' | 'low' {
    const score = this.result()?.score ?? 0;
    if (score >= 80) return 'excellent';
    if (score >= 60) return 'good';
    return 'low';
  }

  /** Mensaje corto que va arriba del score gauge. */
  scoreLabel(): string {
    const tier = this.scoreTier();
    if (tier === 'excellent') return 'Excelente';
    if (tier === 'good') return 'Bueno, mejorable';
    return 'Necesita trabajo';
  }

  /** Mapeo de severity → icon material. Usado por el template. */
  iconFor(severity: string): string {
    if (severity === 'ok') return 'check_circle';
    if (severity === 'critical') return 'error';
    return 'warning';
  }

  close(): void {
    this.closed.emit();
  }
}

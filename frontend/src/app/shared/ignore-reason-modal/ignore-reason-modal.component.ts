import { CommonModule } from '@angular/common';
import {
  ChangeDetectionStrategy,
  Component,
  EventEmitter,
  HostListener,
  Input,
  Output,
} from '@angular/core';

import {
  IGNORE_REASON_LABELS,
  IgnoreReason,
} from '../../models/job-offer.model';

/**
 * Modal chico que pregunta el motivo al ignorar una oferta.
 *
 * No es bloqueante — el user puede "Saltar" y el ignore se ejecuta igual
 * con reason vacio. La friccion extra es intencional pero minima:
 * queremos que el motivo sea la norma sin obligarlo. Las agregaciones
 * de motivos alimentan (a) filtros por default ("el 40% de tus ignores
 * son sueldo bajo → filtramos ofertas sin salario visible"), (b) el
 * ranker personalizado de la Fase 3.
 *
 * Standalone + inline template para no crear scss/html paralelos —
 * el CSS es todo Tailwind. Usado desde results.component y
 * job-detail.component; ambos escuchan (select)/(cancel).
 */
@Component({
  selector: 'app-ignore-reason-modal',
  standalone: true,
  imports: [CommonModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div
      *ngIf="open"
      class="fixed inset-0 z-[200] flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm"
      (click)="onBackdrop($event)"
    >
      <div
        class="glass-strong rounded-2xl w-full max-w-md p-6 shadow-2xl"
        role="dialog"
        aria-modal="true"
        aria-labelledby="ignore-modal-title"
      >
        <h3
          id="ignore-modal-title"
          class="text-lg font-semibold text-bone mb-1"
        >
          ¿Por qué la ignoras?
        </h3>
        <p class="text-sm text-warm-grey mb-5">
          Opcional — nos ayuda a mostrarte mejores ofertas.
        </p>

        <div class="flex flex-wrap gap-2 mb-5">
          <button
            *ngFor="let entry of reasons"
            type="button"
            class="reason-chip"
            (click)="onPick(entry.code)"
          >
            {{ entry.label }}
          </button>
        </div>

        <div class="flex items-center justify-end gap-2">
          <button
            type="button"
            class="text-sm text-warm-grey hover:text-bone px-3 py-2"
            (click)="onSkip()"
          >
            Saltar
          </button>
        </div>
      </div>
    </div>
  `,
  styles: [
    `
      .reason-chip {
        padding: 0.5rem 0.875rem;
        border-radius: 9999px;
        background: rgba(255, 255, 255, 0.06);
        border: 1px solid rgba(255, 255, 255, 0.1);
        color: var(--color-bone, #f5f5f0);
        font-size: 0.8125rem;
        font-weight: 500;
        transition:
          background 0.15s ease,
          border-color 0.15s ease,
          transform 0.1s ease;
      }
      .reason-chip:hover {
        background: rgba(255, 122, 41, 0.15);
        border-color: rgba(255, 122, 41, 0.4);
      }
      .reason-chip:active {
        transform: scale(0.97);
      }
    `,
  ],
})
export class IgnoreReasonModalComponent {
  /** Padre controla la visibilidad. */
  @Input() open = false;

  /** Emite el codigo del motivo elegido — o '' si el user tocó "Saltar" o
   *  cerró el modal con backdrop/Escape. El caller sigue igual: manda al
   *  backend con o sin reason y el flujo de ignore procede. */
  @Output() select = new EventEmitter<IgnoreReason | ''>();

  /** Lista renderable de chips. Deriva del enum del backend via
   *  IGNORE_REASON_LABELS — mantener sincro es 1 solo lugar. */
  readonly reasons: { code: IgnoreReason; label: string }[] = (
    Object.entries(IGNORE_REASON_LABELS) as [IgnoreReason, string][]
  ).map(([code, label]) => ({ code, label }));

  onPick(code: IgnoreReason): void {
    this.select.emit(code);
  }

  onSkip(): void {
    this.select.emit('');
  }

  onBackdrop(event: MouseEvent): void {
    // Click en el fondo (fuera del contenido del dialog) = skip.
    if (event.target === event.currentTarget) {
      this.select.emit('');
    }
  }

  @HostListener('document:keydown.escape')
  onEscape(): void {
    if (this.open) this.select.emit('');
  }
}

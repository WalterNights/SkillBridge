import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { animate, style, transition, trigger } from '@angular/animations';
import { ToastService, Toast } from '../../../services/toast.service';
import { Subscription } from 'rxjs';

@Component({
  selector: 'app-toast-container',
  standalone: true,
  imports: [CommonModule],
  animations: [
    // Enter: desliza desde la derecha + fade + escala muy sutil.
    // Leave: invierte el gesto y se acompasa con un fade más rápido
    // para que la salida no se quede colgada en la atención del user.
    // La curva (0.22, 1, 0.36, 1) es un ease-out-expo suave —
    // arranca enseguida, frena lento al final, sin overshoot.
    trigger('toastAnimation', [
      transition(':enter', [
        style({
          opacity: 0,
          transform: 'translateX(110%) scale(0.96)',
          filter: 'blur(2px)',
        }),
        animate(
          '360ms cubic-bezier(0.22, 1, 0.36, 1)',
          style({ opacity: 1, transform: 'translateX(0) scale(1)', filter: 'blur(0)' }),
        ),
      ]),
      transition(':leave', [
        style({ opacity: 1, transform: 'translateX(0) scale(1)' }),
        animate(
          '260ms cubic-bezier(0.4, 0, 1, 1)',
          style({ opacity: 0, transform: 'translateX(110%) scale(0.96)' }),
        ),
      ]),
    ]),
  ],
  template: `
    <div class="toast-stack">
      <div
        *ngFor="let toast of toasts; trackBy: trackById"
        @toastAnimation
        class="toast"
        [attr.data-type]="toast.type"
      >
        <span class="toast-icon" aria-hidden="true">
          <span class="material-symbols-outlined" style="font-variation-settings: 'FILL' 1">
            {{ iconFor(toast.type) }}
          </span>
        </span>

        <div class="toast-body">
          <p *ngIf="toast.title" class="toast-title">{{ toast.title }}</p>
          <p class="toast-message">{{ toast.message }}</p>
          <button
            *ngIf="toast.action"
            (click)="handleAction(toast)"
            class="toast-action"
          >
            {{ toast.action.label }}
            <span class="material-symbols-outlined" style="font-size: 14px">arrow_forward</span>
          </button>
        </div>

        <button (click)="closeToast(toast.id)" class="toast-close" aria-label="Cerrar">
          <span class="material-symbols-outlined" style="font-size: 18px">close</span>
        </button>

        <div
          *ngIf="toast.duration && toast.duration > 0"
          class="toast-progress"
          aria-hidden="true"
        >
          <span
            class="toast-progress-fill"
            [style.animation-duration.ms]="toast.duration"
          ></span>
        </div>
      </div>
    </div>
  `,
  styles: [
    `
      :host {
        position: fixed;
        inset: 0;
        pointer-events: none;
        z-index: 100;
      }

      .toast-stack {
        position: fixed;
        top: 16px;
        right: 16px;
        display: flex;
        flex-direction: column;
        gap: 10px;
        pointer-events: none;
        max-width: calc(100vw - 32px);
      }

      .toast {
        pointer-events: auto;
        position: relative;
        display: grid;
        grid-template-columns: auto 1fr auto;
        align-items: start;
        gap: 12px;
        width: 380px;
        max-width: 100%;
        padding: 14px 16px 14px 22px;
        background: rgba(20, 22, 28, 0.92);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 14px;
        backdrop-filter: blur(20px) saturate(140%);
        overflow: hidden;
        font-family: inherit;
        color: #e8e5dd;
        /* La banda lateral de color es un inset box-shadow — sigue la
           curva del border-radius perfectamente, sin sub-pixel gaps
           entre un elemento absoluto y el border del padre. El
           drop-shadow y el highlight interno también van acá, todo
           agrupado en un único box-shadow stack. */
        box-shadow:
          inset 4px 0 0 0 var(--toast-accent, #f97316),
          inset 0 0 0 1px rgba(255, 255, 255, 0.02),
          0 18px 40px rgba(0, 0, 0, 0.45);
      }

      .toast[data-type='success'] { --toast-accent: #22c55e; }
      .toast[data-type='error']   { --toast-accent: #ef4444; }
      .toast[data-type='warning'] { --toast-accent: #f59e0b; }
      .toast[data-type='info']    { --toast-accent: #f97316; }

      .toast-icon {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 32px;
        height: 32px;
        border-radius: 10px;
        flex-shrink: 0;
        margin-top: 1px;

        .material-symbols-outlined {
          font-size: 20px;
        }
      }
      .toast[data-type='success'] .toast-icon {
        color: #4ade80;
        background: rgba(34, 197, 94, 0.12);
      }
      .toast[data-type='error'] .toast-icon {
        color: #f87171;
        background: rgba(239, 68, 68, 0.12);
      }
      .toast[data-type='warning'] .toast-icon {
        color: #fbbf24;
        background: rgba(245, 158, 11, 0.12);
      }
      .toast[data-type='info'] .toast-icon {
        color: #fb923c;
        background: rgba(249, 115, 22, 0.12);
      }

      .toast-body {
        min-width: 0;
        flex: 1;
      }

      .toast-title {
        margin: 0 0 2px;
        font-size: 13px;
        font-weight: 700;
        color: #f5f3ed;
        letter-spacing: -0.01em;
      }

      .toast-message {
        margin: 0;
        font-size: 13px;
        line-height: 1.45;
        color: #cfcfc8;
      }

      .toast-action {
        margin-top: 8px;
        display: inline-flex;
        align-items: center;
        gap: 4px;
        padding: 0;
        background: none;
        border: 0;
        cursor: pointer;
        font-family: inherit;
        font-size: 12px;
        font-weight: 700;
        letter-spacing: 0.01em;
        color: var(--toast-accent);
        transition: opacity 140ms ease;

        &:hover { opacity: 0.85; }
      }

      .toast-close {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 26px;
        height: 26px;
        margin: -3px -4px -3px 0;
        background: transparent;
        border: 0;
        border-radius: 8px;
        color: #8b8a85;
        cursor: pointer;
        flex-shrink: 0;
        transition: background 160ms ease, color 160ms ease;

        &:hover {
          background: rgba(255, 255, 255, 0.05);
          color: #e8e5dd;
        }
      }

      /* Progress bar: barra fina en el borde inferior que se vacía con
         la duración del toast. Arranca desde el borde derecho del accent
         lateral (left: 4px) para no superponerse con esa franja. */
      .toast-progress {
        position: absolute;
        left: 4px;
        right: 0;
        bottom: 0;
        height: 2px;
        background: rgba(255, 255, 255, 0.04);
        overflow: hidden;
      }
      .toast-progress-fill {
        display: block;
        height: 100%;
        width: 100%;
        transform-origin: left;
        background: var(--toast-accent);
        animation: toast-shrink linear forwards;
      }

      @keyframes toast-shrink {
        from { transform: scaleX(1); }
        to   { transform: scaleX(0); }
      }
    `,
  ],
})
export class ToastContainerComponent implements OnInit, OnDestroy {
  toasts: Toast[] = [];
  private subscription?: Subscription;

  constructor(private toastService: ToastService) {}

  ngOnInit(): void {
    this.subscription = this.toastService.getToasts().subscribe((toasts) => {
      this.toasts = toasts;
    });
  }

  ngOnDestroy(): void {
    this.subscription?.unsubscribe();
  }

  trackById(_index: number, toast: Toast): string {
    return toast.id;
  }

  closeToast(id: string): void {
    this.toastService.remove(id);
  }

  handleAction(toast: Toast): void {
    if (toast.action) {
      toast.action.callback();
      this.closeToast(toast.id);
    }
  }

  getToastClasses(toast: Toast): string {
    const borderClasses = {
      success: 'border-l-4 border-l-accent-500',
      error: 'border-l-4 border-l-error-500',
      warning: 'border-l-4 border-l-warning-500',
      info: 'border-l-4 border-l-primary-500',
    };

    return borderClasses[toast.type];
  }

  getActionClasses(toast: Toast): string {
    const colorClasses = {
      success: 'text-accent-600 dark:text-accent-400',
      error: 'text-error-600 dark:text-error-400',
      warning: 'text-warning-600 dark:text-warning-400',
      info: 'text-primary-600 dark:text-primary-400',
    };

    return colorClasses[toast.type];
  }

  getProgressClasses(toast: Toast): string {
    const bgClasses = {
      success: 'bg-accent-500',
      error: 'bg-error-500',
      warning: 'bg-warning-500',
      info: 'bg-primary-500',
    };

    return `progress-animate ${bgClasses[toast.type]}`;
  }

  /** Material symbol para cada tipo de toast — usado en el template. */
  iconFor(type: Toast['type']): string {
    switch (type) {
      case 'success':
        return 'check_circle';
      case 'error':
        return 'error';
      case 'warning':
        return 'warning';
      default:
        return 'info';
    }
  }
}

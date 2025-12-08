import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ToastService, Toast } from '../../../services/toast.service';
import { Subscription } from 'rxjs';

@Component({
  selector: 'app-toast-container',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="fixed top-4 right-4 z-[100] flex flex-col gap-2 pointer-events-none">
      <div
        *ngFor="let toast of toasts"
        class="pointer-events-auto w-96 max-w-full bg-white dark:bg-dark-bg-secondary rounded-xl shadow-xl border border-gray-200 dark:border-dark-border overflow-hidden animate-slide-in"
        [class]="getToastClasses(toast)"
      >
        <div class="flex items-start gap-3 p-4">
          <!-- Icon -->
          <div class="flex-shrink-0">
            <svg
              *ngIf="toast.type === 'success'"
              class="h-6 w-6 text-accent-500"
              fill="currentColor"
              viewBox="0 0 20 20"
            >
              <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd" />
            </svg>
            
            <svg
              *ngIf="toast.type === 'error'"
              class="h-6 w-6 text-error-500"
              fill="currentColor"
              viewBox="0 0 20 20"
            >
              <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd" />
            </svg>
            
            <svg
              *ngIf="toast.type === 'warning'"
              class="h-6 w-6 text-warning-500"
              fill="currentColor"
              viewBox="0 0 20 20"
            >
              <path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd" />
            </svg>
            
            <svg
              *ngIf="toast.type === 'info'"
              class="h-6 w-6 text-primary-500"
              fill="currentColor"
              viewBox="0 0 20 20"
            >
              <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clip-rule="evenodd" />
            </svg>
          </div>

          <!-- Content -->
          <div class="flex-1 min-w-0">
            <p
              *ngIf="toast.title"
              class="text-sm font-semibold text-gray-900 dark:text-dark-text-primary"
            >
              {{ toast.title }}
            </p>
            <p class="text-sm text-gray-600 dark:text-dark-text-secondary mt-0.5">
              {{ toast.message }}
            </p>
            
            <!-- Action Button -->
            <button
              *ngIf="toast.action"
              (click)="handleAction(toast)"
              class="mt-2 text-sm font-medium hover:underline"
              [class]="getActionClasses(toast)"
            >
              {{ toast.action.label }}
            </button>
          </div>

          <!-- Close Button -->
          <button
            (click)="closeToast(toast.id)"
            class="flex-shrink-0 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors"
            aria-label="Close"
          >
            <svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <!-- Progress Bar -->
        <div
          *ngIf="toast.duration && toast.duration > 0"
          class="h-1 bg-gray-200 dark:bg-dark-bg-tertiary"
        >
          <div
            class="h-full transition-all ease-linear"
            [class]="getProgressClasses(toast)"
            [style.animation-duration.ms]="toast.duration"
          ></div>
        </div>
      </div>
    </div>
  `,
  styles: [`
    @keyframes shrink {
      from { width: 100%; }
      to { width: 0%; }
    }
    
    .progress-animate {
      animation: shrink linear;
    }
  `]
})
export class ToastContainerComponent implements OnInit, OnDestroy {
  toasts: Toast[] = [];
  private subscription?: Subscription;

  constructor(private toastService: ToastService) {}

  ngOnInit(): void {
    this.subscription = this.toastService.getToasts().subscribe(toasts => {
      this.toasts = toasts;
    });
  }

  ngOnDestroy(): void {
    this.subscription?.unsubscribe();
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
      info: 'border-l-4 border-l-primary-500'
    };
    
    return borderClasses[toast.type];
  }

  getActionClasses(toast: Toast): string {
    const colorClasses = {
      success: 'text-accent-600 dark:text-accent-400',
      error: 'text-error-600 dark:text-error-400',
      warning: 'text-warning-600 dark:text-warning-400',
      info: 'text-primary-600 dark:text-primary-400'
    };
    
    return colorClasses[toast.type];
  }

  getProgressClasses(toast: Toast): string {
    const bgClasses = {
      success: 'bg-accent-500',
      error: 'bg-error-500',
      warning: 'bg-warning-500',
      info: 'bg-primary-500'
    };
    
    return `progress-animate ${bgClasses[toast.type]}`;
  }
}

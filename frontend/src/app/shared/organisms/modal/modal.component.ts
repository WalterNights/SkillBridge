import { Component, Input, Output, EventEmitter, HostListener } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ButtonComponent } from '../../atoms/button/button.component';

@Component({
  selector: 'app-modal',
  standalone: true,
  imports: [CommonModule, ButtonComponent],
  template: `
    <div
      *ngIf="isOpen"
      class="fixed inset-0 z-50 overflow-y-auto"
      [class.animate-fade-in]="isOpen"
    >
      <!-- Backdrop -->
      <div
        (click)="onBackdropClick()"
        class="fixed inset-0 bg-black/50 backdrop-blur-sm transition-opacity"
      ></div>

      <!-- Modal Container -->
      <div class="flex min-h-full items-center justify-center p-4">
        <!-- Modal Content -->
        <div
          class="modal-content relative bg-white dark:bg-dark-bg-secondary rounded-2xl shadow-2xl border border-gray-200 dark:border-dark-border max-h-[90vh] flex flex-col animate-scale-in"
          [class]="getModalSizeClasses()"
          (click)="$event.stopPropagation()"
        >
          <!-- Header -->
          <div
            *ngIf="showHeader"
            class="flex items-center justify-between px-6 py-4 border-b border-gray-200 dark:border-dark-border"
          >
            <div class="flex-1 min-w-0">
              <h3 class="text-lg font-semibold text-gray-900 dark:text-dark-text-primary">
                {{ title }}
              </h3>
              <p *ngIf="subtitle" class="text-sm text-gray-500 dark:text-dark-text-secondary mt-0.5">
                {{ subtitle }}
              </p>
            </div>
            
            <button
              *ngIf="showCloseButton"
              (click)="close()"
              class="flex-shrink-0 ml-4 p-2 rounded-lg text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 hover:bg-gray-100 dark:hover:bg-dark-bg-tertiary transition-colors"
              aria-label="Close"
            >
              <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          <!-- Body -->
          <div
            class="flex-1 overflow-y-auto"
            [class]="getBodyClasses()"
          >
            <ng-content></ng-content>
          </div>

          <!-- Footer -->
          <div
            *ngIf="showFooter"
            class="flex items-center justify-end gap-3 px-6 py-4 border-t border-gray-200 dark:border-dark-border bg-gray-50 dark:bg-dark-bg-tertiary/50"
          >
            <ng-content select="[footer]"></ng-content>
            
            <!-- Default Footer Buttons -->
            <ng-container *ngIf="!hasFooterContent">
              <app-button
                *ngIf="showCancelButton"
                variant="outline"
                (click)="onCancel()"
              >
                {{ cancelLabel }}
              </app-button>
              
              <app-button
                *ngIf="showConfirmButton"
                [variant]="confirmVariant"
                [loading]="loading"
                [disabled]="confirmDisabled"
                (click)="onConfirm()"
              >
                {{ confirmLabel }}
              </app-button>
            </ng-container>
          </div>
        </div>
      </div>
    </div>
  `,
  styles: []
})
export class ModalComponent {
  @Input() isOpen = false;
  @Input() title = '';
  @Input() subtitle = '';
  @Input() size: 'sm' | 'md' | 'lg' | 'xl' | 'full' = 'md';
  @Input() showHeader = true;
  @Input() showFooter = true;
  @Input() showCloseButton = true;
  @Input() showCancelButton = true;
  @Input() showConfirmButton = true;
  @Input() cancelLabel = 'Cancelar';
  @Input() confirmLabel = 'Confirmar';
  @Input() confirmVariant: 'primary' | 'secondary' | 'danger' = 'primary';
  @Input() confirmDisabled = false;
  @Input() loading = false;
  @Input() closeOnBackdrop = true;
  @Input() closeOnEscape = true;
  @Input() padding: 'none' | 'sm' | 'md' | 'lg' = 'md';
  @Input() hasFooterContent = false;

  @Output() close$ = new EventEmitter<void>();
  @Output() confirm = new EventEmitter<void>();
  @Output() cancel = new EventEmitter<void>();

  @HostListener('document:keydown.escape', ['$event'])
  handleEscape(event: KeyboardEvent): void {
    if (this.isOpen && this.closeOnEscape) {
      this.close();
    }
  }

  close(): void {
    this.isOpen = false;
    this.close$.emit();
  }

  onBackdropClick(): void {
    if (this.closeOnBackdrop) {
      this.close();
    }
  }

  onConfirm(): void {
    this.confirm.emit();
  }

  onCancel(): void {
    this.cancel.emit();
    this.close();
  }

  getModalSizeClasses(): string {
    const sizeClasses = {
      sm: 'w-full max-w-sm',
      md: 'w-full max-w-md',
      lg: 'w-full max-w-2xl',
      xl: 'w-full max-w-4xl',
      full: 'w-full max-w-7xl'
    };
    
    return sizeClasses[this.size];
  }

  getBodyClasses(): string {
    const paddingClasses = {
      none: '',
      sm: 'px-4 py-3',
      md: 'px-6 py-4',
      lg: 'px-8 py-6'
    };
    
    return paddingClasses[this.padding];
  }
}

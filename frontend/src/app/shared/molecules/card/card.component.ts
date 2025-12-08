import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-card',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div [class]="getCardClasses()">
      <!-- Header -->
      <div *ngIf="hasHeader" class="flex items-start justify-between mb-4">
        <div class="flex-1">
          <h3 *ngIf="title" class="text-lg font-semibold text-gray-900 dark:text-dark-text-primary">
            {{ title }}
          </h3>
          <p *ngIf="subtitle" class="text-sm text-gray-500 dark:text-dark-text-secondary mt-1">
            {{ subtitle }}
          </p>
        </div>
        <ng-content select="[header-actions]"></ng-content>
      </div>

      <!-- Body -->
      <div [class]="getBodyClasses()">
        <ng-content></ng-content>
      </div>

      <!-- Footer -->
      <div *ngIf="hasFooter" class="mt-4 pt-4 border-t border-gray-100 dark:border-dark-border">
        <ng-content select="[footer]"></ng-content>
      </div>
    </div>
  `,
  styles: []
})
export class CardComponent {
  @Input() title = '';
  @Input() subtitle = '';
  @Input() variant: 'default' | 'elevated' | 'outline' | 'glass' = 'default';
  @Input() padding: 'none' | 'sm' | 'md' | 'lg' = 'md';
  @Input() hoverable = false;
  @Input() clickable = false;
  @Input() hasHeader = false;
  @Input() hasFooter = false;

  getCardClasses(): string {
    const baseClasses = 'rounded-xl transition-all duration-300';
    
    const variantClasses = {
      default: 'bg-white dark:bg-dark-bg-secondary border border-gray-200 dark:border-dark-border',
      elevated: 'bg-white dark:bg-dark-bg-secondary shadow-lg',
      outline: 'border-2 border-gray-300 dark:border-dark-border bg-transparent',
      glass: 'glass backdrop-blur-md border border-white/20 dark:border-dark-border/20'
    };
    
    const paddingClasses = {
      none: '',
      sm: 'p-3',
      md: 'p-6',
      lg: 'p-8'
    };
    
    const interactionClasses = [];
    if (this.hoverable) {
      interactionClasses.push('hover:shadow-xl hover:-translate-y-1');
    }
    if (this.clickable) {
      interactionClasses.push('cursor-pointer active:scale-98');
    }
    
    return `${baseClasses} ${variantClasses[this.variant]} ${paddingClasses[this.padding]} ${interactionClasses.join(' ')}`.trim();
  }

  getBodyClasses(): string {
    return this.hasHeader || this.hasFooter ? '' : '';
  }
}

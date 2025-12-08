import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';

type BadgeVariant = 'primary' | 'secondary' | 'accent' | 'warning' | 'error' | 'gray';
type BadgeSize = 'sm' | 'md' | 'lg';

@Component({
  selector: 'app-badge',
  standalone: true,
  imports: [CommonModule],
  template: `
    <span [class]="getClasses()">
      <span *ngIf="dot" class="h-2 w-2 rounded-full mr-1.5" [class]="getDotClasses()"></span>
      <ng-content></ng-content>
    </span>
  `,
  styles: []
})
export class BadgeComponent {
  @Input() variant: BadgeVariant = 'gray';
  @Input() size: BadgeSize = 'md';
  @Input() dot = false;
  @Input() pill = false;

  getClasses(): string {
    const baseClasses = 'inline-flex items-center font-medium';
    
    const variantClasses: Record<BadgeVariant, string> = {
      primary: 'bg-primary-50 text-primary-700 dark:bg-primary-900/20 dark:text-primary-400',
      secondary: 'bg-secondary-50 text-secondary-700 dark:bg-secondary-900/20 dark:text-secondary-400',
      accent: 'bg-accent-50 text-accent-700 dark:bg-accent-900/20 dark:text-accent-400',
      warning: 'bg-warning-50 text-warning-700 dark:bg-warning-900/20 dark:text-warning-400',
      error: 'bg-error-50 text-error-700 dark:bg-error-900/20 dark:text-error-400',
      gray: 'bg-gray-100 text-gray-700 dark:bg-dark-bg-tertiary dark:text-gray-300'
    };
    
    const sizeClasses: Record<BadgeSize, string> = {
      sm: 'px-2 py-0.5 text-xs',
      md: 'px-3 py-1 text-sm',
      lg: 'px-4 py-1.5 text-base'
    };
    
    const shapeClasses = this.pill ? 'rounded-full' : 'rounded-lg';
    
    return `${baseClasses} ${variantClasses[this.variant]} ${sizeClasses[this.size]} ${shapeClasses}`.trim();
  }

  getDotClasses(): string {
    const dotColors: Record<BadgeVariant, string> = {
      primary: 'bg-primary-500',
      secondary: 'bg-secondary-500',
      accent: 'bg-accent-500',
      warning: 'bg-warning-500',
      error: 'bg-error-500',
      gray: 'bg-gray-500'
    };
    
    return `animate-pulse ${dotColors[this.variant]}`;
  }
}

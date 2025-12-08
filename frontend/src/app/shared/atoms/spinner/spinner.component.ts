import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';

type SpinnerSize = 'xs' | 'sm' | 'md' | 'lg' | 'xl';

@Component({
  selector: 'app-spinner',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div [class]="getContainerClasses()">
      <svg [class]="getSpinnerClasses()" fill="none" viewBox="0 0 24 24">
        <circle 
          class="opacity-25" 
          cx="12" 
          cy="12" 
          r="10" 
          stroke="currentColor" 
          stroke-width="4"
        ></circle>
        <path 
          class="opacity-75" 
          fill="currentColor" 
          d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
        ></path>
      </svg>
      <span *ngIf="label" class="ml-2 text-sm font-medium">{{ label }}</span>
    </div>
  `,
  styles: []
})
export class SpinnerComponent {
  @Input() size: SpinnerSize = 'md';
  @Input() label = '';
  @Input() color: 'primary' | 'white' | 'gray' = 'primary';
  @Input() center = false;

  getContainerClasses(): string {
    const baseClasses = 'inline-flex items-center';
    const centerClasses = this.center ? 'justify-center w-full' : '';
    return `${baseClasses} ${centerClasses}`.trim();
  }

  getSpinnerClasses(): string {
    const sizeClasses: Record<SpinnerSize, string> = {
      xs: 'h-3 w-3',
      sm: 'h-4 w-4',
      md: 'h-6 w-6',
      lg: 'h-8 w-8',
      xl: 'h-12 w-12'
    };
    
    const colorClasses = {
      primary: 'text-primary-600 dark:text-primary-400',
      white: 'text-white',
      gray: 'text-gray-600 dark:text-gray-400'
    };
    
    return `animate-spin ${sizeClasses[this.size]} ${colorClasses[this.color]}`.trim();
  }
}

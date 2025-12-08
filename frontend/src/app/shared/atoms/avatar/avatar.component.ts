import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';

type AvatarSize = 'xs' | 'sm' | 'md' | 'lg' | 'xl';

@Component({
  selector: 'app-avatar',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div [class]="getClasses()">
      <img 
        *ngIf="src && !imageError" 
        [src]="src" 
        [alt]="alt"
        (error)="onImageError()"
        class="w-full h-full object-cover"
      />
      <div *ngIf="!src || imageError" class="flex items-center justify-center w-full h-full bg-gradient-to-br from-primary-500 to-secondary-500 text-white font-semibold">
        {{ getInitials() }}
      </div>
      <span *ngIf="status" [class]="getStatusClasses()"></span>
    </div>
  `,
  styles: []
})
export class AvatarComponent {
  @Input() src = '';
  @Input() alt = '';
  @Input() name = '';
  @Input() size: AvatarSize = 'md';
  @Input() status: 'online' | 'offline' | 'away' | '' = '';
  @Input() ring = false;

  imageError = false;

  onImageError(): void {
    this.imageError = true;
  }

  getInitials(): string {
    if (!this.name) return '?';
    
    const parts = this.name.trim().split(' ');
    if (parts.length >= 2) {
      return (parts[0][0] + parts[1][0]).toUpperCase();
    }
    return this.name.substring(0, 2).toUpperCase();
  }

  getClasses(): string {
    const baseClasses = 'relative inline-flex items-center justify-center rounded-full overflow-hidden';
    
    const sizeClasses: Record<AvatarSize, string> = {
      xs: 'h-6 w-6 text-xs',
      sm: 'h-8 w-8 text-sm',
      md: 'h-10 w-10 text-base',
      lg: 'h-12 w-12 text-lg',
      xl: 'h-16 w-16 text-xl'
    };
    
    const ringClasses = this.ring ? 'ring-2 ring-white dark:ring-dark-bg-secondary ring-offset-2' : '';
    
    return `${baseClasses} ${sizeClasses[this.size]} ${ringClasses}`.trim();
  }

  getStatusClasses(): string {
    const baseClasses = 'absolute bottom-0 right-0 block rounded-full ring-2 ring-white dark:ring-dark-bg-secondary';
    
    const sizeClasses: Record<AvatarSize, string> = {
      xs: 'h-1.5 w-1.5',
      sm: 'h-2 w-2',
      md: 'h-2.5 w-2.5',
      lg: 'h-3 w-3',
      xl: 'h-4 w-4'
    };
    
    const statusColors = {
      online: 'bg-accent-500',
      offline: 'bg-gray-400',
      away: 'bg-warning-500',
      '': ''
    };
    
    return `${baseClasses} ${sizeClasses[this.size]} ${statusColors[this.status]}`.trim();
  }
}

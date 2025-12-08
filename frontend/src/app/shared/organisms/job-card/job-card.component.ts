import { Component, Input, Output, EventEmitter } from '@angular/core';
import { CommonModule } from '@angular/common';
import { BadgeComponent } from '../../atoms/badge/badge.component';
import { ButtonComponent } from '../../atoms/button/button.component';

export interface JobOffer {
  id: string;
  title: string;
  company: string;
  companyLogo?: string;
  location: string;
  salary?: string;
  type: string;
  remote: boolean;
  matchPercentage: number;
  skills: string[];
  matchingSkills?: number;
  totalSkills?: number;
  postedDate: string;
  description?: string;
}

@Component({
  selector: 'app-job-card',
  standalone: true,
  imports: [CommonModule, BadgeComponent, ButtonComponent],
  template: `
    <div
      class="group relative bg-white dark:bg-dark-bg-secondary rounded-2xl p-6 border border-gray-200 dark:border-dark-border hover:border-primary-500 dark:hover:border-primary-500 transition-all duration-300 hover:shadow-xl hover:-translate-y-1 cursor-pointer"
      (click)="onCardClick()"
    >
      
      <!-- Match Badge -->
      <div class="absolute -top-3 -right-3 z-10">
        <div class="relative">
          <div
            class="w-16 h-16 rounded-full flex items-center justify-center shadow-lg"
            [class]="getMatchBadgeClasses()"
          >
            <span class="text-white font-bold text-sm">{{ job.matchPercentage }}%</span>
          </div>
          <div
            *ngIf="job.matchPercentage >= 80"
            class="absolute inset-0 rounded-full animate-ping opacity-30"
            [class]="getMatchBadgeClasses()"
          ></div>
        </div>
      </div>
      
      <!-- Company Info -->
      <div class="flex items-start gap-4 mb-4">
        <div class="w-14 h-14 rounded-xl bg-gray-100 dark:bg-dark-bg-tertiary flex items-center justify-center shrink-0 overflow-hidden">
          <img
            *ngIf="job.companyLogo"
            [src]="job.companyLogo"
            [alt]="job.company"
            class="w-10 h-10 object-contain"
          />
          <svg
            *ngIf="!job.companyLogo"
            class="w-8 h-8 text-gray-400"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
          </svg>
        </div>
        
        <div class="flex-1 min-w-0">
          <h3 class="text-lg font-semibold text-gray-900 dark:text-dark-text-primary truncate group-hover:text-primary-600 dark:group-hover:text-primary-400 transition-colors">
            {{ job.title }}
          </h3>
          <p class="text-sm text-gray-600 dark:text-dark-text-secondary">{{ job.company }}</p>
        </div>

        <!-- Favorite Button -->
        <button
          (click)="onFavoriteClick($event)"
          class="flex-shrink-0 p-2 rounded-lg text-gray-400 hover:text-error-500 hover:bg-error-50 dark:hover:bg-error-900/20 transition-colors"
          [class.text-error-500]="isFavorite"
          aria-label="Favorite"
        >
          <svg class="w-5 h-5" [class.fill-current]="isFavorite" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z" />
          </svg>
        </button>
      </div>
      
      <!-- Job Details -->
      <div class="flex flex-wrap gap-2 mb-4">
        <app-badge variant="primary" size="sm">
          <svg class="w-3 h-3 mr-1" fill="currentColor" viewBox="0 0 20 20">
            <path fill-rule="evenodd" d="M5.05 4.05a7 7 0 119.9 9.9L10 18.9l-4.95-4.95a7 7 0 010-9.9zM10 11a2 2 0 100-4 2 2 0 000 4z" clip-rule="evenodd" />
          </svg>
          {{ job.location }}
        </app-badge>
        
        <app-badge
          *ngIf="job.remote"
          variant="secondary"
          size="sm"
        >
          Remoto
        </app-badge>
        
        <app-badge
          *ngIf="job.salary"
          variant="accent"
          size="sm"
        >
          <svg class="w-3 h-3 mr-1" fill="currentColor" viewBox="0 0 20 20">
            <path d="M8.433 7.418c.155-.103.346-.196.567-.267v1.698a2.305 2.305 0 01-.567-.267C8.07 8.34 8 8.114 8 8c0-.114.07-.34.433-.582zM11 12.849v-1.698c.22.071.412.164.567.267.364.243.433.468.433.582 0 .114-.07.34-.433.582a2.305 2.305 0 01-.567.267z" />
            <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-13a1 1 0 10-2 0v.092a4.535 4.535 0 00-1.676.662C6.602 6.234 6 7.009 6 8c0 .99.602 1.765 1.324 2.246.48.32 1.054.545 1.676.662v1.941c-.391-.127-.68-.317-.843-.504a1 1 0 10-1.51 1.31c.562.649 1.413 1.076 2.353 1.253V15a1 1 0 102 0v-.092a4.535 4.535 0 001.676-.662C13.398 13.766 14 12.991 14 12c0-.99-.602-1.765-1.324-2.246A4.535 4.535 0 0011 9.092V7.151c.391.127.68.317.843.504a1 1 0 101.511-1.31c-.563-.649-1.413-1.076-2.354-1.253V5z" clip-rule="evenodd" />
          </svg>
          {{ job.salary }}
        </app-badge>
        
        <app-badge variant="warning" size="sm">
          {{ job.type }}
        </app-badge>
      </div>
      
      <!-- Skills Match -->
      <div class="mb-4">
        <div class="flex items-center justify-between mb-2">
          <span class="text-xs font-medium text-gray-500 dark:text-dark-text-secondary">
            Skills coincidentes
          </span>
          <span
            class="text-xs font-semibold"
            [class]="getSkillsMatchClasses()"
          >
            {{ job.matchingSkills || 0 }}/{{ job.totalSkills || job.skills.length }}
          </span>
        </div>
        
        <!-- Skills List -->
        <div class="flex flex-wrap gap-1">
          <span
            *ngFor="let skill of displaySkills"
            class="px-2 py-1 text-xs bg-gray-100 dark:bg-dark-bg-tertiary text-gray-700 dark:text-gray-300 rounded"
          >
            {{ skill }}
          </span>
          <span
            *ngIf="remainingSkillsCount > 0"
            class="px-2 py-1 text-xs bg-primary-50 dark:bg-primary-900/20 text-primary-700 dark:text-primary-400 rounded font-medium"
          >
            +{{ remainingSkillsCount }} más
          </span>
        </div>
      </div>
      
      <!-- Description Preview -->
      <p
        *ngIf="job.description && showDescription"
        class="text-sm text-gray-600 dark:text-dark-text-secondary line-clamp-2 mb-4"
      >
        {{ job.description }}
      </p>
      
      <!-- Footer -->
      <div class="flex items-center justify-between pt-4 border-t border-gray-100 dark:border-dark-border">
        <span class="text-xs text-gray-500 dark:text-dark-text-secondary flex items-center gap-1">
          <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          {{ job.postedDate }}
        </span>
        
        <button
          (click)="onViewDetails($event)"
          class="inline-flex items-center text-sm font-medium text-primary-600 hover:text-primary-700 dark:text-primary-400 dark:hover:text-primary-300 transition-colors group"
        >
          Ver detalles
          <svg class="ml-1 w-4 h-4 group-hover:translate-x-1 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
          </svg>
        </button>
      </div>
    </div>
  `,
  styles: [`
    .line-clamp-2 {
      display: -webkit-box;
      -webkit-line-clamp: 2;
      -webkit-box-orient: vertical;
      overflow: hidden;
    }
  `]
})
export class JobCardComponent {
  @Input() job!: JobOffer;
  @Input() isFavorite = false;
  @Input() showDescription = true;
  @Input() maxSkillsDisplay = 3;

  @Output() cardClick = new EventEmitter<JobOffer>();
  @Output() viewDetails = new EventEmitter<JobOffer>();
  @Output() favoriteToggle = new EventEmitter<JobOffer>();

  get displaySkills(): string[] {
    return this.job.skills.slice(0, this.maxSkillsDisplay);
  }

  get remainingSkillsCount(): number {
    return Math.max(0, this.job.skills.length - this.maxSkillsDisplay);
  }

  onCardClick(): void {
    this.cardClick.emit(this.job);
  }

  onViewDetails(event: Event): void {
    event.stopPropagation();
    this.viewDetails.emit(this.job);
  }

  onFavoriteClick(event: Event): void {
    event.stopPropagation();
    this.favoriteToggle.emit(this.job);
  }

  getMatchBadgeClasses(): string {
    const percentage = this.job.matchPercentage;
    
    if (percentage >= 80) {
      return 'bg-gradient-to-br from-green-400 to-green-600';
    } else if (percentage >= 60) {
      return 'bg-gradient-to-br from-blue-400 to-blue-600';
    } else if (percentage >= 40) {
      return 'bg-gradient-to-br from-yellow-400 to-yellow-600';
    } else {
      return 'bg-gradient-to-br from-gray-400 to-gray-600';
    }
  }

  getSkillsMatchClasses(): string {
    const matchingSkills = this.job.matchingSkills || 0;
    const totalSkills = this.job.totalSkills || this.job.skills.length;
    const percentage = (matchingSkills / totalSkills) * 100;
    
    if (percentage >= 80) {
      return 'text-accent-600 dark:text-accent-400';
    } else if (percentage >= 60) {
      return 'text-primary-600 dark:text-primary-400';
    } else if (percentage >= 40) {
      return 'text-warning-600 dark:text-warning-400';
    } else {
      return 'text-gray-600 dark:text-gray-400';
    }
  }
}

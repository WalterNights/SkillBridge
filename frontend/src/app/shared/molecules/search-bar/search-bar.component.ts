import { Component, Input, Output, EventEmitter, ViewChild, ElementRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';

@Component({
  selector: 'app-search-bar',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="relative" [class.w-full]="fullWidth">
      <!-- Search Input -->
      <div class="relative">
        <!-- Search Icon -->
        <div class="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
          <svg 
            class="h-5 w-5 text-gray-400 dark:text-gray-500" 
            fill="none" 
            stroke="currentColor" 
            viewBox="0 0 24 24"
          >
            <path 
              stroke-linecap="round" 
              stroke-linejoin="round" 
              stroke-width="2" 
              d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" 
            />
          </svg>
        </div>

        <!-- Input -->
        <input
          #searchInput
          type="text"
          [(ngModel)]="searchQuery"
          (input)="onSearchChange()"
          (keyup.enter)="onSearch()"
          (focus)="onFocus()"
          (blur)="onBlur()"
          [placeholder]="placeholder"
          [disabled]="disabled"
          [class]="getInputClasses()"
        />

        <!-- Clear Button -->
        <button
          *ngIf="searchQuery && showClearButton"
          (click)="clearSearch()"
          class="absolute inset-y-0 right-0 pr-3 flex items-center text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors"
          type="button"
          aria-label="Clear search"
        >
          <svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>

        <!-- Loading Spinner -->
        <div
          *ngIf="loading"
          class="absolute inset-y-0 right-0 pr-3 flex items-center pointer-events-none"
        >
          <svg class="animate-spin h-5 w-5 text-primary-600" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
          </svg>
        </div>
      </div>

      <!-- Search Suggestions Dropdown -->
      <div
        *ngIf="isFocused && suggestions.length > 0 && searchQuery"
        class="absolute z-50 w-full mt-2 bg-white dark:bg-dark-bg-secondary border border-gray-200 dark:border-dark-border rounded-xl shadow-lg max-h-60 overflow-y-auto"
      >
        <button
          *ngFor="let suggestion of suggestions; let i = index"
          (click)="selectSuggestion(suggestion)"
          class="w-full px-4 py-2 text-left text-sm text-gray-700 dark:text-dark-text-primary hover:bg-gray-50 dark:hover:bg-dark-bg-tertiary transition-colors first:rounded-t-xl last:rounded-b-xl"
          [class.bg-gray-50]="i === selectedSuggestionIndex"
          type="button"
        >
          <div class="flex items-center gap-3">
            <svg class="h-4 w-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
            <span>{{ suggestion }}</span>
          </div>
        </button>
      </div>

      <!-- Recent Searches -->
      <div
        *ngIf="isFocused && recentSearches.length > 0 && !searchQuery && showRecentSearches"
        class="absolute z-50 w-full mt-2 bg-white dark:bg-dark-bg-secondary border border-gray-200 dark:border-dark-border rounded-xl shadow-lg"
      >
        <div class="px-4 py-2 text-xs font-semibold text-gray-500 dark:text-gray-400 border-b border-gray-100 dark:border-dark-border">
          Búsquedas recientes
        </div>
        <button
          *ngFor="let search of recentSearches"
          (click)="selectSuggestion(search)"
          class="w-full px-4 py-2 text-left text-sm text-gray-700 dark:text-dark-text-primary hover:bg-gray-50 dark:hover:bg-dark-bg-tertiary transition-colors flex items-center justify-between group"
          type="button"
        >
          <div class="flex items-center gap-3">
            <svg class="h-4 w-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <span>{{ search }}</span>
          </div>
          <button
            (click)="removeRecentSearch(search, $event)"
            class="opacity-0 group-hover:opacity-100 text-gray-400 hover:text-error-500 transition-all"
            type="button"
            aria-label="Remove"
          >
            <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </button>
      </div>
    </div>
  `,
  styles: []
})
export class SearchBarComponent {
  @Input() placeholder = 'Buscar...';
  @Input() disabled = false;
  @Input() loading = false;
  @Input() fullWidth = true;
  @Input() size: 'sm' | 'md' | 'lg' = 'md';
  @Input() suggestions: string[] = [];
  @Input() recentSearches: string[] = [];
  @Input() showClearButton = true;
  @Input() showRecentSearches = true;
  @Input() debounceTime = 300;

  @Output() search = new EventEmitter<string>();
  @Output() searchChange = new EventEmitter<string>();
  @Output() clear = new EventEmitter<void>();

  @ViewChild('searchInput') searchInputRef!: ElementRef<HTMLInputElement>;

  searchQuery = '';
  isFocused = false;
  selectedSuggestionIndex = -1;
  private debounceTimer: any;

  onSearchChange(): void {
    clearTimeout(this.debounceTimer);
    this.debounceTimer = setTimeout(() => {
      this.searchChange.emit(this.searchQuery);
    }, this.debounceTime);
  }

  onSearch(): void {
    if (this.searchQuery.trim()) {
      this.search.emit(this.searchQuery);
      this.isFocused = false;
    }
  }

  onFocus(): void {
    this.isFocused = true;
  }

  onBlur(): void {
    // Delay to allow click on suggestions
    setTimeout(() => {
      this.isFocused = false;
    }, 200);
  }

  clearSearch(): void {
    this.searchQuery = '';
    this.clear.emit();
    this.searchChange.emit('');
    this.searchInputRef?.nativeElement.focus();
  }

  selectSuggestion(suggestion: string): void {
    this.searchQuery = suggestion;
    this.search.emit(suggestion);
    this.isFocused = false;
  }

  removeRecentSearch(search: string, event: Event): void {
    event.stopPropagation();
    const index = this.recentSearches.indexOf(search);
    if (index > -1) {
      this.recentSearches.splice(index, 1);
    }
  }

  getInputClasses(): string {
    const baseClasses = 'block w-full pl-10 bg-white dark:bg-dark-bg-tertiary border border-gray-300 dark:border-dark-border rounded-xl text-gray-900 dark:text-dark-text-primary placeholder-gray-400 dark:placeholder-gray-500 focus:ring-2 focus:ring-primary-500 focus:border-transparent transition-all duration-200';
    
    const sizeClasses = {
      sm: 'py-2 pr-3 text-sm',
      md: 'py-3 pr-10 text-base',
      lg: 'py-4 pr-12 text-lg'
    };
    
    const disabledClasses = this.disabled ? 'opacity-50 cursor-not-allowed' : '';
    
    return `${baseClasses} ${sizeClasses[this.size]} ${disabledClasses}`.trim();
  }

  focus(): void {
    this.searchInputRef?.nativeElement.focus();
  }
}

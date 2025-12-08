import { Component, Input, Output, EventEmitter } from '@angular/core';
import { CommonModule } from '@angular/common';

export interface DropdownOption {
  label: string;
  value: any;
  icon?: string;
  disabled?: boolean;
  divider?: boolean;
}

@Component({
  selector: 'app-dropdown',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="relative inline-block text-left" [class.w-full]="fullWidth">
      <!-- Trigger Button -->
      <button
        type="button"
        (click)="toggleDropdown()"
        (keydown.escape)="closeDropdown()"
        [disabled]="disabled"
        [class]="getButtonClasses()"
        [attr.aria-expanded]="isOpen"
        [attr.aria-haspopup]="true"
      >
        <span class="flex items-center gap-2">
          <ng-content select="[trigger-icon]"></ng-content>
          <span>{{ selectedLabel || placeholder }}</span>
        </span>
        <svg
          class="ml-2 h-5 w-5 transition-transform duration-200"
          [class.rotate-180]="isOpen"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      <!-- Dropdown Menu -->
      <div
        *ngIf="isOpen"
        class="absolute z-50 mt-2 bg-white dark:bg-dark-bg-secondary rounded-xl shadow-lg border border-gray-200 dark:border-dark-border overflow-hidden animate-scale-in"
        [class.w-full]="fullWidth"
        [class.w-56]="!fullWidth"
        [ngClass]="getPositionClasses()"
      >
        <!-- Search -->
        <div *ngIf="searchable" class="p-2 border-b border-gray-100 dark:border-dark-border">
          <input
            type="text"
            [(ngModel)]="searchQuery"
            (input)="onSearchChange()"
            placeholder="Buscar..."
            class="w-full px-3 py-2 text-sm border border-gray-300 dark:border-dark-border rounded-lg bg-white dark:bg-dark-bg-tertiary text-gray-900 dark:text-dark-text-primary focus:ring-2 focus:ring-primary-500 focus:border-transparent"
          />
        </div>

        <!-- Options List -->
        <div class="max-h-60 overflow-y-auto py-1">
          <ng-container *ngFor="let option of filteredOptions; let i = index">
            <!-- Divider -->
            <div
              *ngIf="option.divider"
              class="my-1 border-t border-gray-200 dark:border-dark-border"
            ></div>

            <!-- Option -->
            <button
              *ngIf="!option.divider"
              type="button"
              (click)="selectOption(option)"
              [disabled]="option.disabled"
              class="w-full px-4 py-2 text-left text-sm transition-colors flex items-center justify-between group"
              [class]="getOptionClasses(option)"
            >
              <div class="flex items-center gap-3 flex-1">
                <!-- Icon -->
                <span *ngIf="option.icon" class="text-gray-400 dark:text-gray-500">
                  {{ option.icon }}
                </span>
                <!-- Label -->
                <span class="truncate">{{ option.label }}</span>
              </div>
              <!-- Selected Check -->
              <svg
                *ngIf="isSelected(option)"
                class="h-4 w-4 text-primary-600 dark:text-primary-400"
                fill="currentColor"
                viewBox="0 0 20 20"
              >
                <path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd" />
              </svg>
            </button>
          </ng-container>

          <!-- No Results -->
          <div
            *ngIf="searchable && searchQuery && filteredOptions.length === 0"
            class="px-4 py-3 text-sm text-gray-500 dark:text-gray-400 text-center"
          >
            No se encontraron resultados
          </div>

          <!-- Empty State -->
          <div
            *ngIf="options.length === 0"
            class="px-4 py-3 text-sm text-gray-500 dark:text-gray-400 text-center"
          >
            Sin opciones disponibles
          </div>
        </div>
      </div>

      <!-- Backdrop -->
      <div
        *ngIf="isOpen"
        (click)="closeDropdown()"
        class="fixed inset-0 z-40"
      ></div>
    </div>
  `,
  styles: []
})
export class DropdownComponent {
  @Input() options: DropdownOption[] = [];
  @Input() selectedValue: any = null;
  @Input() placeholder = 'Seleccionar...';
  @Input() disabled = false;
  @Input() searchable = false;
  @Input() fullWidth = false;
  @Input() position: 'left' | 'right' = 'left';
  @Input() variant: 'default' | 'outline' | 'ghost' = 'default';

  @Output() selectionChange = new EventEmitter<any>();

  isOpen = false;
  searchQuery = '';
  filteredOptions: DropdownOption[] = [];

  ngOnInit(): void {
    this.filteredOptions = [...this.options];
  }

  ngOnChanges(): void {
    this.filteredOptions = [...this.options];
  }

  get selectedLabel(): string {
    const selected = this.options.find(opt => opt.value === this.selectedValue);
    return selected?.label || '';
  }

  toggleDropdown(): void {
    if (!this.disabled) {
      this.isOpen = !this.isOpen;
      if (this.isOpen) {
        this.searchQuery = '';
        this.filteredOptions = [...this.options];
      }
    }
  }

  closeDropdown(): void {
    this.isOpen = false;
    this.searchQuery = '';
  }

  selectOption(option: DropdownOption): void {
    if (!option.disabled) {
      this.selectedValue = option.value;
      this.selectionChange.emit(option.value);
      this.closeDropdown();
    }
  }

  isSelected(option: DropdownOption): boolean {
    return this.selectedValue === option.value;
  }

  onSearchChange(): void {
    const query = this.searchQuery.toLowerCase();
    this.filteredOptions = this.options.filter(option =>
      option.label.toLowerCase().includes(query)
    );
  }

  getButtonClasses(): string {
    const baseClasses = 'inline-flex items-center justify-between w-full px-4 py-2 text-sm font-medium rounded-xl transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-primary-500';
    
    const variantClasses = {
      default: 'bg-white dark:bg-dark-bg-tertiary border border-gray-300 dark:border-dark-border text-gray-700 dark:text-dark-text-primary hover:bg-gray-50 dark:hover:bg-dark-bg-primary',
      outline: 'border-2 border-gray-300 dark:border-dark-border text-gray-700 dark:text-dark-text-primary hover:border-primary-600 dark:hover:border-primary-500',
      ghost: 'text-gray-700 dark:text-dark-text-primary hover:bg-gray-100 dark:hover:bg-dark-bg-tertiary'
    };
    
    const disabledClasses = this.disabled ? 'opacity-50 cursor-not-allowed' : '';
    
    return `${baseClasses} ${variantClasses[this.variant]} ${disabledClasses}`.trim();
  }

  getOptionClasses(option: DropdownOption): string {
    const baseClasses = 'text-gray-700 dark:text-dark-text-primary';
    const hoverClasses = 'hover:bg-gray-50 dark:hover:bg-dark-bg-tertiary';
    const selectedClasses = this.isSelected(option) 
      ? 'bg-primary-50 dark:bg-primary-900/20 text-primary-700 dark:text-primary-400' 
      : '';
    const disabledClasses = option.disabled 
      ? 'opacity-50 cursor-not-allowed' 
      : '';
    
    return `${baseClasses} ${hoverClasses} ${selectedClasses} ${disabledClasses}`.trim();
  }

  getPositionClasses(): string {
    return this.position === 'right' ? 'right-0' : 'left-0';
  }
}

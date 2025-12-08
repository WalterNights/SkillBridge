import { Component, Input, forwardRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ControlValueAccessor, NG_VALUE_ACCESSOR, FormsModule } from '@angular/forms';

/**
 * Type definitions for ControlValueAccessor callbacks
 */
type OnChangeFn = (value: string) => void;
type OnTouchedFn = () => void;

/**
 * Reusable input component with form control integration
 */
@Component({
  selector: 'app-input',
  standalone: true,
  imports: [CommonModule, FormsModule],
  providers: [
    {
      provide: NG_VALUE_ACCESSOR,
      useExisting: forwardRef(() => InputComponent),
      multi: true
    }
  ],
  template: `
    <div class="space-y-2">
      <label *ngIf="label" [for]="id" class="block text-sm font-medium text-gray-700 dark:text-dark-text-primary">
        {{ label }}
        <span *ngIf="required" class="text-error-500">*</span>
      </label>
      
      <div class="relative">
        <div *ngIf="icon" class="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
          <ng-content select="[icon]"></ng-content>
        </div>
        
        <input
          [id]="id"
          [type]="type"
          [placeholder]="placeholder"
          [disabled]="disabled"
          [required]="required"
          [(ngModel)]="value"
          (blur)="onTouched()"
          (input)="onChange(($event.target as HTMLInputElement).value)"
          [class]="getInputClasses()"
        />
        
        <div *ngIf="error" class="absolute inset-y-0 right-0 pr-3 flex items-center pointer-events-none">
          <svg class="h-5 w-5 text-error-500" fill="currentColor" viewBox="0 0 20 20">
            <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clip-rule="evenodd" />
          </svg>
        </div>
      </div>
      
      <p *ngIf="error" class="text-xs text-error-500">{{ error }}</p>
      <p *ngIf="hint && !error" class="text-xs text-gray-500 dark:text-dark-text-secondary">{{ hint }}</p>
    </div>
  `,
  styles: []
})
export class InputComponent implements ControlValueAccessor {
  @Input() id = `input-${Math.random().toString(36).substring(2, 9)}`;
  @Input() label = '';
  @Input() type: 'text' | 'email' | 'password' | 'number' | 'tel' | 'url' = 'text';
  @Input() placeholder = '';
  @Input() disabled = false;
  @Input() required = false;
  @Input() error = '';
  @Input() hint = '';
  @Input() icon = false;

  value = '';
  
  onChange: OnChangeFn = () => {};
  onTouched: OnTouchedFn = () => {};

  /**
   * Writes a new value to the element
   */
  writeValue(value: string | null): void {
    this.value = value ?? '';
  }

  /**
   * Registers a callback function for value changes
   */
  registerOnChange(fn: OnChangeFn): void {
    this.onChange = fn;
  }

  /**
   * Registers a callback function for touch events
   */
  registerOnTouched(fn: OnTouchedFn): void {
    this.onTouched = fn;
  }

  setDisabledState(isDisabled: boolean): void {
    this.disabled = isDisabled;
  }

  getInputClasses(): string {
    const baseClasses = 'block w-full py-3 bg-white dark:bg-dark-bg-tertiary border rounded-xl text-gray-900 dark:text-dark-text-primary placeholder-gray-400 dark:placeholder-gray-500 focus:ring-2 focus:border-transparent transition-all duration-200';
    
    const paddingClasses = this.icon ? 'pl-10 pr-3' : 'px-3';
    
    const stateClasses = this.error
      ? 'border-error-500 focus:ring-error-500'
      : 'border-gray-300 dark:border-dark-border focus:ring-primary-500';
    
    const disabledClasses = this.disabled ? 'opacity-50 cursor-not-allowed' : '';
    
    return `${baseClasses} ${paddingClasses} ${stateClasses} ${disabledClasses}`.trim();
  }
}

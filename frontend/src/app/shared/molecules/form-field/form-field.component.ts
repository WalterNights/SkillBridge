import { Component, Input, forwardRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ControlValueAccessor, NG_VALUE_ACCESSOR, FormsModule } from '@angular/forms';

@Component({
  selector: 'app-form-field',
  standalone: true,
  imports: [CommonModule, FormsModule],
  providers: [
    {
      provide: NG_VALUE_ACCESSOR,
      useExisting: forwardRef(() => FormFieldComponent),
      multi: true
    }
  ],
  template: `
    <div class="space-y-2">
      <!-- Label -->
      <label 
        *ngIf="label" 
        [for]="id" 
        class="block text-sm font-medium text-gray-700 dark:text-dark-text-primary"
      >
        {{ label }}
        <span *ngIf="required" class="text-error-500 ml-0.5">*</span>
      </label>

      <!-- Input Container -->
      <div class="relative">
        <!-- Left Icon -->
        <div 
          *ngIf="leftIcon" 
          class="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none"
        >
          <ng-content select="[leftIcon]"></ng-content>
        </div>

        <!-- Input/Textarea -->
        <input
          *ngIf="type !== 'textarea'"
          [id]="id"
          [type]="type"
          [placeholder]="placeholder"
          [disabled]="disabled"
          [required]="required"
          [(ngModel)]="value"
          (blur)="onTouched()"
          (input)="onChange($any($event.target).value)"
          [class]="getInputClasses()"
          [attr.aria-describedby]="getAriaDescribedBy()"
          [attr.aria-invalid]="!!error"
        />

        <textarea
          *ngIf="type === 'textarea'"
          [id]="id"
          [placeholder]="placeholder"
          [disabled]="disabled"
          [required]="required"
          [rows]="rows"
          [(ngModel)]="value"
          (blur)="onTouched()"
          (input)="onChange($any($event.target).value)"
          [class]="getInputClasses()"
          [attr.aria-describedby]="getAriaDescribedBy()"
          [attr.aria-invalid]="!!error"
        ></textarea>

        <!-- Right Icon/Error Icon -->
        <div 
          *ngIf="rightIcon || error" 
          class="absolute inset-y-0 right-0 pr-3 flex items-center"
          [class.pointer-events-none]="!rightIcon"
        >
          <ng-container *ngIf="error && !rightIcon">
            <svg class="h-5 w-5 text-error-500" fill="currentColor" viewBox="0 0 20 20">
              <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clip-rule="evenodd" />
            </svg>
          </ng-container>
          <ng-container *ngIf="rightIcon && !error">
            <ng-content select="[rightIcon]"></ng-content>
          </ng-container>
        </div>

        <!-- Character Counter -->
        <div 
          *ngIf="maxLength && type === 'textarea'" 
          class="absolute bottom-2 right-2 text-xs text-gray-400 dark:text-gray-500"
        >
          {{ value?.length || 0 }}/{{ maxLength }}
        </div>
      </div>

      <!-- Error Message -->
      <p 
        *ngIf="error" 
        [id]="id + '-error'" 
        class="text-xs text-error-500 flex items-center gap-1"
      >
        <svg class="h-3 w-3" fill="currentColor" viewBox="0 0 20 20">
          <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd" />
        </svg>
        {{ error }}
      </p>

      <!-- Hint Message -->
      <p 
        *ngIf="hint && !error" 
        [id]="id + '-hint'" 
        class="text-xs text-gray-500 dark:text-dark-text-secondary"
      >
        {{ hint }}
      </p>

      <!-- Success Message -->
      <p 
        *ngIf="success && !error" 
        [id]="id + '-success'" 
        class="text-xs text-accent-600 dark:text-accent-400 flex items-center gap-1"
      >
        <svg class="h-3 w-3" fill="currentColor" viewBox="0 0 20 20">
          <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd" />
        </svg>
        {{ success }}
      </p>
    </div>
  `,
  styles: []
})
export class FormFieldComponent implements ControlValueAccessor {
  @Input() id = `form-field-${Math.random().toString(36).substring(2, 9)}`;
  @Input() label = '';
  @Input() type: 'text' | 'email' | 'password' | 'number' | 'tel' | 'url' | 'textarea' = 'text';
  @Input() placeholder = '';
  @Input() disabled = false;
  @Input() required = false;
  @Input() error = '';
  @Input() hint = '';
  @Input() success = '';
  @Input() leftIcon = false;
  @Input() rightIcon = false;
  @Input() rows = 4;
  @Input() maxLength = 0;

  value = '';
  
  onChange: any = () => {};
  onTouched: any = () => {};

  writeValue(value: any): void {
    this.value = value || '';
  }

  registerOnChange(fn: any): void {
    this.onChange = fn;
  }

  registerOnTouched(fn: any): void {
    this.onTouched = fn;
  }

  setDisabledState(isDisabled: boolean): void {
    this.disabled = isDisabled;
  }

  getInputClasses(): string {
    const baseClasses = 'block w-full bg-white dark:bg-dark-bg-tertiary border rounded-xl text-gray-900 dark:text-dark-text-primary placeholder-gray-400 dark:placeholder-gray-500 focus:ring-2 focus:border-transparent transition-all duration-200';
    
    const typeClasses = this.type === 'textarea' ? 'py-3 resize-none' : 'py-3';
    
    const paddingClasses = [];
    if (this.leftIcon) paddingClasses.push('pl-10');
    else paddingClasses.push('pl-3');
    
    if (this.rightIcon || this.error) paddingClasses.push('pr-10');
    else paddingClasses.push('pr-3');
    
    const stateClasses = this.error
      ? 'border-error-500 focus:ring-error-500'
      : this.success
      ? 'border-accent-500 focus:ring-accent-500'
      : 'border-gray-300 dark:border-dark-border focus:ring-primary-500';
    
    const disabledClasses = this.disabled 
      ? 'opacity-50 cursor-not-allowed bg-gray-50 dark:bg-dark-bg-primary' 
      : '';
    
    return `${baseClasses} ${typeClasses} ${paddingClasses.join(' ')} ${stateClasses} ${disabledClasses}`.trim();
  }

  getAriaDescribedBy(): string | null {
    if (this.error) return `${this.id}-error`;
    if (this.success) return `${this.id}-success`;
    if (this.hint) return `${this.id}-hint`;
    return null;
  }
}

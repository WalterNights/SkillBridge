import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ThemeService } from '../../../services/theme.service';

@Component({
  selector: 'app-theme-toggle',
  standalone: true,
  imports: [CommonModule],
  template: `
    <button
      (click)="toggleTheme()"
      class="relative inline-flex items-center justify-center p-2 rounded-lg transition-colors duration-200 hover:bg-gray-100 dark:hover:bg-dark-bg-tertiary focus:outline-none focus:ring-2 focus:ring-primary-500"
      [attr.aria-label]="isDarkMode() ? 'Switch to light mode' : 'Switch to dark mode'"
    >
      <!-- Sun Icon (Light Mode) -->
      <svg
        *ngIf="!isDarkMode()"
        class="h-5 w-5 text-gray-700 transition-transform duration-300 rotate-0"
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
      >
        <path
          stroke-linecap="round"
          stroke-linejoin="round"
          stroke-width="2"
          d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z"
        />
      </svg>

      <!-- Moon Icon (Dark Mode) -->
      <svg
        *ngIf="isDarkMode()"
        class="h-5 w-5 text-gray-300 transition-transform duration-300 -rotate-90"
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
      >
        <path
          stroke-linecap="round"
          stroke-linejoin="round"
          stroke-width="2"
          d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z"
        />
      </svg>
    </button>
  `,
  styles: []
})
export class ThemeToggleComponent {
  constructor(public themeService: ThemeService) {}

  get isDarkMode() {
    return this.themeService.isDarkMode;
  }

  toggleTheme(): void {
    this.themeService.toggleTheme();
  }
}

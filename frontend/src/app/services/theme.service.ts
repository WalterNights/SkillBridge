import { Injectable, signal, effect } from '@angular/core';

@Injectable({
  providedIn: 'root'
})
export class ThemeService {
  private readonly THEME_KEY = 'skillbridge-theme';
  
  // Signal for reactive theme state
  isDarkMode = signal<boolean>(false);

  constructor() {
    this.initializeTheme();
    
    // Effect to update DOM when theme changes
    effect(() => {
      this.applyTheme(this.isDarkMode());
    });
  }

  private initializeTheme(): void {
    // Check for saved theme preference or default to system preference
    const savedTheme = localStorage.getItem(this.THEME_KEY);
    
    if (savedTheme) {
      this.isDarkMode.set(savedTheme === 'dark');
    } else {
      // Check system preference
      const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
      this.isDarkMode.set(prefersDark);
    }

    // Listen for system theme changes
    window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
      if (!localStorage.getItem(this.THEME_KEY)) {
        this.isDarkMode.set(e.matches);
      }
    });
  }

  private applyTheme(isDark: boolean): void {
    const html = document.documentElement;
    const body = document.body;

    if (isDark) {
      html.classList.add('dark');
      body.classList.add('dark');
    } else {
      html.classList.remove('dark');
      body.classList.remove('dark');
    }

    // Save preference
    localStorage.setItem(this.THEME_KEY, isDark ? 'dark' : 'light');
  }

  toggleTheme(): void {
    this.isDarkMode.update(value => !value);
  }

  setTheme(isDark: boolean): void {
    this.isDarkMode.set(isDark);
  }

  getCurrentTheme(): 'light' | 'dark' {
    return this.isDarkMode() ? 'dark' : 'light';
  }
}

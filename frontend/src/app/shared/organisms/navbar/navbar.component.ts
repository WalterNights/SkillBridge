import { Component, Input, Output, EventEmitter } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { ThemeToggleComponent } from '../../atoms/theme-toggle/theme-toggle.component';
import { AvatarComponent } from '../../atoms/avatar/avatar.component';
import { ButtonComponent } from '../../atoms/button/button.component';

export interface NavItem {
  label: string;
  route?: string;
  icon?: string;
  children?: NavItem[];
  badge?: number;
  action?: () => void;
}

@Component({
  selector: 'app-navbar',
  standalone: true,
  imports: [CommonModule, RouterModule, ThemeToggleComponent, AvatarComponent, ButtonComponent],
  template: `
    <nav class="fixed top-0 left-0 right-0 z-50 bg-white/80 dark:bg-dark-bg-secondary/80 backdrop-blur-md border-b border-gray-200 dark:border-dark-border">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div class="flex items-center justify-between h-16">
          <!-- Logo & Brand -->
          <div class="flex items-center gap-3">
            <a [routerLink]="logoRoute" class="flex items-center gap-3 group">
              <div class="w-10 h-10 bg-gradient-to-br from-primary-500 to-secondary-500 rounded-xl flex items-center justify-center transition-transform group-hover:scale-105">
                <svg class="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
                </svg>
              </div>
              <span class="text-xl font-bold text-gray-900 dark:text-white hidden sm:block">
                {{ brandName }}
              </span>
            </a>
          </div>

          <!-- Desktop Navigation -->
          <div class="hidden md:flex items-center gap-1">
            <ng-container *ngFor="let item of navItems">
              <a
                *ngIf="!item.action"
                [routerLink]="item.route"
                routerLinkActive="text-primary-600 dark:text-primary-400 bg-primary-50 dark:bg-primary-900/20"
                class="px-4 py-2 rounded-lg text-sm font-medium text-gray-700 dark:text-dark-text-secondary hover:text-primary-600 dark:hover:text-primary-400 hover:bg-gray-50 dark:hover:bg-dark-bg-tertiary transition-all duration-200 relative"
              >
                {{ item.label }}
                <span
                  *ngIf="item.badge"
                  class="absolute -top-1 -right-1 px-1.5 py-0.5 text-xs font-bold bg-error-500 text-white rounded-full"
                >
                  {{ item.badge > 99 ? '99+' : item.badge }}
                </span>
              </a>
              
              <button
                *ngIf="item.action"
                (click)="item.action()"
                class="px-4 py-2 rounded-lg text-sm font-medium text-gray-700 dark:text-dark-text-secondary hover:text-primary-600 dark:hover:text-primary-400 hover:bg-gray-50 dark:hover:bg-dark-bg-tertiary transition-all duration-200"
              >
                {{ item.label }}
              </button>
            </ng-container>
          </div>

          <!-- Right Actions -->
          <div class="flex items-center gap-3">
            <!-- Theme Toggle -->
            <app-theme-toggle></app-theme-toggle>

            <!-- Notifications -->
            <button
              *ngIf="showNotifications"
              (click)="onNotificationsClick()"
              class="relative p-2 rounded-lg text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-dark-bg-tertiary transition-colors"
              aria-label="Notifications"
            >
              <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
              </svg>
              <span
                *ngIf="notificationCount > 0"
                class="absolute top-1 right-1 h-2 w-2 bg-error-500 rounded-full animate-pulse"
              ></span>
            </button>

            <!-- User Menu -->
            <div *ngIf="showUserMenu" class="relative">
              <button
                (click)="toggleUserMenu()"
                class="flex items-center gap-2 p-1 rounded-lg hover:bg-gray-100 dark:hover:bg-dark-bg-tertiary transition-colors"
              >
                <app-avatar
                  [src]="userAvatar"
                  [name]="userName"
                  [status]="userStatus"
                  size="md"
                ></app-avatar>
                <svg
                  class="w-4 h-4 text-gray-600 dark:text-gray-400 transition-transform"
                  [class.rotate-180]="isUserMenuOpen"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
                </svg>
              </button>

              <!-- User Dropdown -->
              <div
                *ngIf="isUserMenuOpen"
                class="absolute right-0 mt-2 w-56 bg-white dark:bg-dark-bg-secondary rounded-xl shadow-lg border border-gray-200 dark:border-dark-border overflow-hidden animate-scale-in"
              >
                <div class="px-4 py-3 border-b border-gray-100 dark:border-dark-border">
                  <p class="text-sm font-semibold text-gray-900 dark:text-dark-text-primary">
                    {{ userName }}
                  </p>
                  <p class="text-xs text-gray-500 dark:text-dark-text-secondary mt-0.5">
                    {{ userEmail }}
                  </p>
                </div>
                
                <div class="py-1">
                  <a
                    *ngFor="let item of userMenuItems"
                    [routerLink]="item.route"
                    (click)="closeUserMenu()"
                    class="flex items-center gap-3 px-4 py-2 text-sm text-gray-700 dark:text-dark-text-primary hover:bg-gray-50 dark:hover:bg-dark-bg-tertiary transition-colors"
                  >
                    <span [innerHTML]="item.icon"></span>
                    {{ item.label }}
                  </a>
                </div>

                <div class="border-t border-gray-100 dark:border-dark-border py-1">
                  <button
                    (click)="onLogout()"
                    class="w-full flex items-center gap-3 px-4 py-2 text-sm text-error-600 dark:text-error-400 hover:bg-error-50 dark:hover:bg-error-900/20 transition-colors"
                  >
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
                    </svg>
                    Cerrar sesión
                  </button>
                </div>
              </div>

              <!-- Backdrop -->
              <div
                *ngIf="isUserMenuOpen"
                (click)="closeUserMenu()"
                class="fixed inset-0 z-40"
              ></div>
            </div>

            <!-- CTA Button -->
            <app-button
              *ngIf="showCTA"
              variant="primary"
              size="sm"
              (click)="onCTAClick()"
            >
              {{ ctaLabel }}
            </app-button>

            <!-- Mobile Menu Button -->
            <button
              (click)="toggleMobileMenu()"
              class="md:hidden p-2 rounded-lg text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-dark-bg-tertiary transition-colors"
              aria-label="Menu"
            >
              <svg
                *ngIf="!isMobileMenuOpen"
                class="w-6 h-6"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16" />
              </svg>
              <svg
                *ngIf="isMobileMenuOpen"
                class="w-6 h-6"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>

        <!-- Mobile Menu -->
        <div
          *ngIf="isMobileMenuOpen"
          class="md:hidden py-4 border-t border-gray-200 dark:border-dark-border animate-slide-down"
        >
          <div class="flex flex-col gap-2">
            <a
              *ngFor="let item of navItems"
              [routerLink]="item.route"
              (click)="closeMobileMenu()"
              routerLinkActive="text-primary-600 dark:text-primary-400 bg-primary-50 dark:bg-primary-900/20"
              class="px-4 py-2 rounded-lg text-sm font-medium text-gray-700 dark:text-dark-text-secondary hover:bg-gray-50 dark:hover:bg-dark-bg-tertiary transition-colors"
            >
              {{ item.label }}
            </a>
          </div>
        </div>
      </div>
    </nav>

    <!-- Spacer for fixed navbar -->
    <div class="h-16"></div>
  `,
  styles: []
})
export class NavbarComponent {
  @Input() brandName = 'SkillBridge';
  @Input() logoRoute = '/';
  @Input() navItems: NavItem[] = [];
  @Input() userMenuItems: NavItem[] = [];
  @Input() showNotifications = true;
  @Input() showUserMenu = true;
  @Input() showCTA = false;
  @Input() ctaLabel = 'Get Started';
  @Input() userName = 'Usuario';
  @Input() userEmail = 'user@example.com';
  @Input() userAvatar = '';
  @Input() userStatus: 'online' | 'offline' | 'away' | '' = 'online';
  @Input() notificationCount = 0;

  @Output() notificationsClick = new EventEmitter<void>();
  @Output() ctaClick = new EventEmitter<void>();
  @Output() logout = new EventEmitter<void>();

  isUserMenuOpen = false;
  isMobileMenuOpen = false;

  toggleUserMenu(): void {
    this.isUserMenuOpen = !this.isUserMenuOpen;
  }

  closeUserMenu(): void {
    this.isUserMenuOpen = false;
  }

  toggleMobileMenu(): void {
    this.isMobileMenuOpen = !this.isMobileMenuOpen;
  }

  closeMobileMenu(): void {
    this.isMobileMenuOpen = false;
  }

  onNotificationsClick(): void {
    this.notificationsClick.emit();
  }

  onCTAClick(): void {
    this.ctaClick.emit();
  }

  onLogout(): void {
    this.closeUserMenu();
    this.logout.emit();
  }
}

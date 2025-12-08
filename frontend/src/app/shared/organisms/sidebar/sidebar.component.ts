import { Component, Input, Output, EventEmitter } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { BadgeComponent } from '../../atoms/badge/badge.component';

export interface SidebarItem {
  label: string;
  icon: string;
  route?: string;
  badge?: number;
  children?: SidebarItem[];
  action?: () => void;
}

@Component({
  selector: 'app-sidebar',
  standalone: true,
  imports: [CommonModule, RouterModule, BadgeComponent],
  template: `
    <aside
      class="fixed left-0 top-16 h-[calc(100vh-4rem)] bg-white dark:bg-dark-bg-secondary border-r border-gray-200 dark:border-dark-border transition-all duration-300 z-40"
      [class.w-64]="!collapsed"
      [class.w-20]="collapsed"
    >
      <div class="flex flex-col h-full">
        <!-- Toggle Button -->
        <button
          (click)="toggleCollapse()"
          class="absolute -right-3 top-4 w-6 h-6 bg-white dark:bg-dark-bg-secondary border border-gray-200 dark:border-dark-border rounded-full flex items-center justify-center shadow-sm hover:shadow-md transition-all"
        >
          <svg
            class="w-3 h-3 text-gray-600 dark:text-gray-400 transition-transform"
            [class.rotate-180]="collapsed"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" />
          </svg>
        </button>

        <!-- Navigation -->
        <nav class="flex-1 overflow-y-auto py-4 px-3">
          <div class="space-y-1">
            <ng-container *ngFor="let item of items">
              <!-- Item without children -->
              <a
                *ngIf="!item.children && item.route"
                [routerLink]="item.route"
                routerLinkActive="bg-primary-50 dark:bg-primary-900/20 text-primary-600 dark:text-primary-400"
                [routerLinkActiveOptions]="{ exact: false }"
                class="group flex items-center gap-3 px-3 py-2 rounded-lg text-gray-700 dark:text-dark-text-secondary hover:bg-gray-50 dark:hover:bg-dark-bg-tertiary transition-all duration-200"
                [title]="collapsed ? item.label : ''"
              >
                <span [innerHTML]="item.icon" class="w-5 h-5 flex-shrink-0"></span>
                <span *ngIf="!collapsed" class="flex-1 text-sm font-medium">{{ item.label }}</span>
                <app-badge
                  *ngIf="!collapsed && item.badge"
                  variant="error"
                  size="sm"
                  pill
                >
                  {{ item.badge > 99 ? '99+' : item.badge }}
                </app-badge>
              </a>

              <!-- Item with action -->
              <button
                *ngIf="!item.children && item.action"
                (click)="item.action()"
                class="w-full group flex items-center gap-3 px-3 py-2 rounded-lg text-gray-700 dark:text-dark-text-secondary hover:bg-gray-50 dark:hover:bg-dark-bg-tertiary transition-all duration-200"
                [title]="collapsed ? item.label : ''"
              >
                <span [innerHTML]="item.icon" class="w-5 h-5 flex-shrink-0"></span>
                <span *ngIf="!collapsed" class="flex-1 text-sm font-medium text-left">{{ item.label }}</span>
              </button>

              <!-- Item with children -->
              <div *ngIf="item.children">
                <button
                  (click)="toggleGroup(item.label)"
                  class="w-full group flex items-center gap-3 px-3 py-2 rounded-lg text-gray-700 dark:text-dark-text-secondary hover:bg-gray-50 dark:hover:bg-dark-bg-tertiary transition-all duration-200"
                  [title]="collapsed ? item.label : ''"
                >
                  <span [innerHTML]="item.icon" class="w-5 h-5 flex-shrink-0"></span>
                  <span *ngIf="!collapsed" class="flex-1 text-sm font-medium text-left">{{ item.label }}</span>
                  <svg
                    *ngIf="!collapsed"
                    class="w-4 h-4 transition-transform"
                    [class.rotate-180]="expandedGroups.has(item.label)"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
                  </svg>
                </button>

                <!-- Submenu -->
                <div
                  *ngIf="!collapsed && expandedGroups.has(item.label)"
                  class="ml-8 mt-1 space-y-1 animate-fade-in"
                >
                  <a
                    *ngFor="let child of item.children"
                    [routerLink]="child.route"
                    routerLinkActive="text-primary-600 dark:text-primary-400 font-medium"
                    class="block px-3 py-2 text-sm text-gray-600 dark:text-dark-text-secondary hover:text-gray-900 dark:hover:text-dark-text-primary rounded-lg hover:bg-gray-50 dark:hover:bg-dark-bg-tertiary transition-colors"
                  >
                    {{ child.label }}
                  </a>
                </div>
              </div>
            </ng-container>
          </div>
        </nav>

        <!-- Footer -->
        <div *ngIf="showFooter" class="border-t border-gray-200 dark:border-dark-border p-3">
          <ng-content select="[footer]"></ng-content>
        </div>
      </div>
    </aside>

    <!-- Spacer -->
    <div
      class="transition-all duration-300"
      [class.w-64]="!collapsed"
      [class.w-20]="collapsed"
    ></div>

    <!-- Mobile Overlay -->
    <div
      *ngIf="mobileOpen"
      (click)="closeMobile()"
      class="fixed inset-0 bg-black/50 z-30 md:hidden"
    ></div>
  `,
  styles: []
})
export class SidebarComponent {
  @Input() items: SidebarItem[] = [];
  @Input() collapsed = false;
  @Input() showFooter = false;
  @Input() mobileOpen = false;

  @Output() collapsedChange = new EventEmitter<boolean>();
  @Output() mobileOpenChange = new EventEmitter<boolean>();

  expandedGroups = new Set<string>();

  toggleCollapse(): void {
    this.collapsed = !this.collapsed;
    this.collapsedChange.emit(this.collapsed);
    
    // Close all groups when collapsing
    if (this.collapsed) {
      this.expandedGroups.clear();
    }
  }

  toggleGroup(label: string): void {
    if (this.expandedGroups.has(label)) {
      this.expandedGroups.delete(label);
    } else {
      this.expandedGroups.add(label);
    }
  }

  closeMobile(): void {
    this.mobileOpen = false;
    this.mobileOpenChange.emit(false);
  }
}

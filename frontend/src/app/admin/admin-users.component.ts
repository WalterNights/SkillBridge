import { CommonModule } from '@angular/common';
import { HttpErrorResponse } from '@angular/common/http';
import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Title } from '@angular/platform-browser';

import { User } from '../models/user.model';
import { AdminService, AdminStats } from '../services/admin.service';
import { DashboardService } from '../services/dashboard.service';

/**
 * Panel admin: lista de usuarios registrados.
 *
 * Vive DENTRO del AppShell (sidebar + topbar los provee el wrapper).
 * El backend lockea el endpoint con `IsAdminUser` — un user normal
 * recibe 403 si tipea la URL a mano, además del AdminGuard del router.
 */
@Component({
  selector: 'app-admin-users',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './admin-users.component.html',
  styleUrls: ['./admin-users.component.scss'],
})
export class AdminUsersComponent implements OnInit {
  private dashboardService = inject(DashboardService);
  private adminService = inject(AdminService);
  private titleService = inject(Title);

  users = signal<User[]>([]);
  stats = signal<AdminStats | null>(null);
  isLoading = signal(true);
  errorMessage = signal('');

  /** Filtro de búsqueda — matchea contra nombre, email o profession. */
  searchTerm = signal('');

  filteredUsers = computed(() => {
    const term = this.searchTerm().trim().toLowerCase();
    if (!term) return this.users();
    return this.users().filter((u) => {
      const haystack = [
        u.first_name,
        u.last_name,
        u.email,
        u.user?.email,
        u.professional_title,
        u.city,
      ]
        .filter(Boolean)
        .join(' ')
        .toLowerCase();
      return haystack.includes(term);
    });
  });

  constructor() {
    this.titleService.setTitle('SkilTak — Admin · Usuarios');
  }

  ngOnInit(): void {
    this.loadUsers();
    this.loadStats();
  }

  private loadUsers(): void {
    this.isLoading.set(true);
    this.dashboardService.getUsers().subscribe({
      next: (data) => {
        this.users.set(data);
        this.isLoading.set(false);
      },
      error: (err: HttpErrorResponse) => {
        console.error('Failed to load users:', err);
        this.errorMessage.set(
          err.status === 403
            ? 'No tenés permisos para ver esta sección.'
            : 'Error al cargar usuarios.',
        );
        this.isLoading.set(false);
      },
    });
  }

  private loadStats(): void {
    this.adminService.getStats().subscribe({
      next: (data) => this.stats.set(data),
      error: () => {
        /* Soft-fail: la lista funciona sin stats; las cards quedan en 0. */
      },
    });
  }

  /** Iniciales del avatar — fallback al username si no hay first/last. */
  initials(u: User): string {
    const first = (u.first_name ?? u.username ?? '?').charAt(0);
    const last = (u.last_name ?? '').charAt(0);
    return (first + last).toUpperCase();
  }

  /** Email principal del user — el backend a veces lo anida en .user. */
  emailOf(u: User): string {
    return u.user?.email ?? u.email ?? '';
  }

  trackUser(_index: number, user: User): number {
    return user.id;
  }
}

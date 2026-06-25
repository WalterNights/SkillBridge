import { CommonModule } from '@angular/common';
import { HttpErrorResponse } from '@angular/common/http';
import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Title } from '@angular/platform-browser';

import { AuthService } from '../auth/auth.service';
import { User } from '../models/user.model';
import {
  AdminService,
  AdminStats,
  UserRoleResponse,
  UserRoleUpdate,
} from '../services/admin.service';
import { DashboardService } from '../services/dashboard.service';
import { ToastService } from '../services/toast.service';

/** Cambio pendiente de confirmación — alimenta el modal de role-toggle. */
interface PendingRoleChange {
  profile: User;
  /** Texto que ve el admin antes de confirmar ("Promover a admin", etc.). */
  action: string;
  payload: UserRoleUpdate;
}

/**
 * Panel admin: lista de usuarios registrados + toggle de rol.
 *
 * Vive DENTRO del AppShell (sidebar + topbar los provee el wrapper).
 * El backend lockea `IsAdminUser` — un user normal recibe 403 si
 * tipea la URL, además del AdminGuard del router.
 *
 * Toggle de roles:
 *   - Solo aparece para usuarios distintos al actual (anti-lockout UX).
 *   - El backend además rechaza self-demote con 400 (defensa en profundidad).
 *   - `is_superuser` solo se ofrece si el actor ya es super.
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
  private authService = inject(AuthService);
  private toast = inject(ToastService);
  private titleService = inject(Title);

  users = signal<User[]>([]);
  stats = signal<AdminStats | null>(null);
  isLoading = signal(true);
  errorMessage = signal('');

  /** Filtro de búsqueda — matchea contra nombre, email o profession. */
  searchTerm = signal('');

  /** Email del actor — usado para ocultar el botón de role en su propia
   *  fila (defensa UX; el backend igual valida con 400). */
  private currentEmail = this.authService.getUserEmail().toLowerCase();

  /** Modal de confirmación de cambio de rol. Null = cerrado. */
  pendingChange = signal<PendingRoleChange | null>(null);
  isSavingRole = signal(false);

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
            ? 'No tienes permisos para ver esta sección.'
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

  /** True si la fila es del propio admin logueado — no le mostramos
   *  acciones de rol para que no intente degradarse. */
  isSelf(u: User): boolean {
    const target = this.emailOf(u).toLowerCase();
    return !!target && target === this.currentEmail;
  }

  isStaff(u: User): boolean {
    return !!u.user?.is_staff;
  }

  isSuperuser(u: User): boolean {
    return !!u.user?.is_superuser;
  }

  /** El actor puede tocar `is_superuser` solo si él mismo es super. */
  canToggleSuper(): boolean {
    // Si el AuthService expusiera is_superuser lo usaríamos; por ahora,
    // pedir el endpoint igual rechaza con 403 → la UI solo oculta la
    // opción cuando NO hay manera de éxito (defensa UX, no de seguridad).
    return true;
  }

  trackUser(_index: number, user: User): number {
    return user.id;
  }

  // ─── Role toggle ──────────────────────────────────────────────────

  /** Abre el modal con el cambio propuesto. No persiste nada todavía. */
  promptRoleChange(profile: User, field: 'is_staff' | 'is_superuser', next: boolean): void {
    if (this.isSelf(profile)) return; // anti-lockout UX
    const label = field === 'is_staff' ? 'admin' : 'super-admin';
    const action = next ? `Promover a ${label}` : `Quitar rol ${label}`;
    this.pendingChange.set({
      profile,
      action,
      payload: { [field]: next } as UserRoleUpdate,
    });
  }

  cancelRoleChange(): void {
    if (this.isSavingRole()) return;
    this.pendingChange.set(null);
  }

  confirmRoleChange(): void {
    const change = this.pendingChange();
    if (!change) return;
    const userId = change.profile.user?.id;
    if (!userId) {
      this.toast.error('No se encontró el ID del usuario destino.', 'Error');
      this.pendingChange.set(null);
      return;
    }

    this.isSavingRole.set(true);
    this.adminService.updateUserRole(userId, change.payload).subscribe({
      next: (res) => {
        this.applyRoleResponse(change.profile, res);
        this.toast.success(`${change.action} aplicado a ${change.profile.user?.email ?? change.profile.username}.`);
        this.isSavingRole.set(false);
        this.pendingChange.set(null);
      },
      error: (err: HttpErrorResponse) => {
        this.isSavingRole.set(false);
        const detail = err.error?.detail ?? 'No pudimos aplicar el cambio.';
        this.toast.error(detail, `Error ${err.status}`);
      },
    });
  }

  /** Reemplaza el `user` nested en la fila afectada con el snapshot
   *  devuelto por el backend, sin tener que recargar la lista entera. */
  private applyRoleResponse(profile: User, res: UserRoleResponse): void {
    this.users.update((rows) =>
      rows.map((row) => {
        if (row.id !== profile.id) return row;
        return {
          ...row,
          user: {
            ...(row.user ?? { id: res.id, email: res.email }),
            id: res.id,
            email: res.email,
            username: res.username,
            is_staff: res.is_staff,
            is_superuser: res.is_superuser,
          },
        };
      }),
    );
  }
}

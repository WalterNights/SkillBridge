import { CommonModule } from '@angular/common';
import { Component, DestroyRef, HostListener, computed, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { Router, RouterModule } from '@angular/router';
import { AuthService } from '../../auth/auth.service';

/**
 * Stub local de notificaciones — desaparece cuando exista el modelo
 * `Notification` en el backend. Mantenemos las tres categorías que
 * pidió el producto (No leídas / Leídas / Guardadas) y un `read` flag
 * para validar la UX de marcar como leído antes de tener el endpoint.
 */
type NotifKind = 'match' | 'reminder' | 'system';
interface Notification {
  id: number;
  kind: NotifKind;
  title: string;
  body: string;
  createdAt: string;
  read: boolean;
  saved: boolean;
}

const STUB_NOTIFICATIONS: Notification[] = [
  {
    id: 1,
    kind: 'match',
    title: '5 nuevas ofertas calzan con tu perfil',
    body: 'Senior Full Stack, Backend Lead y 3 más — todas con +70% match.',
    createdAt: 'hace 1 hora',
    read: false,
    saved: false,
  },
  {
    id: 2,
    kind: 'reminder',
    title: 'Completá tu portafolio',
    body: 'Sumar tu URL personal aumenta las visitas al perfil un 30%.',
    createdAt: 'hace 3 días',
    read: false,
    saved: true,
  },
  {
    id: 3,
    kind: 'system',
    title: 'Tu CV ATS quedó actualizado',
    body: 'La última edición se aplicó al PDF descargable.',
    createdAt: 'hace 5 días',
    read: true,
    saved: false,
  },
];

type NotifTab = 'unread' | 'read' | 'saved';

/**
 * User chrome compartido: campanita + avatar dropdown.
 *
 * El bell abre un drawer lateral derecho con tres pestañas
 * (No leídas / Leídas / Guardadas). El dot rojo en el bell aparece
 * solo cuando hay al menos una notif no leída.
 *
 * Data stub hasta que el backend de Notification esté listo — el
 * contrato del array es lo único que tendría que cambiar.
 */
@Component({
  selector: 'app-user-nav',
  standalone: true,
  imports: [CommonModule, RouterModule],
  templateUrl: './user-nav.component.html',
  styleUrl: './user-nav.component.scss',
})
export class UserNavComponent {
  private auth = inject(AuthService);
  private router = inject(Router);
  private destroyRef = inject(DestroyRef);

  isLoggedIn = signal(this.auth.isAuthenticated());
  userMenuOpen = signal(false);
  notificationsOpen = signal(false);
  notifTab = signal<NotifTab>('unread');

  userName = signal(this.auth.getUserName());
  userEmail = signal(this.auth.getUserEmail());
  userInitial = computed(() => this.userName().charAt(0).toUpperCase() || 'U');

  notifications = signal<Notification[]>(STUB_NOTIFICATIONS);
  unreadCount = computed(() => this.notifications().filter((n) => !n.read).length);
  visibleNotifications = computed(() => {
    const tab = this.notifTab();
    return this.notifications().filter((n) => {
      if (tab === 'unread') return !n.read;
      if (tab === 'read') return n.read;
      return n.saved;
    });
  });

  constructor() {
    this.auth.isLoggedIn$.pipe(takeUntilDestroyed(this.destroyRef)).subscribe((loggedIn) => {
      this.isLoggedIn.set(loggedIn);
      this.userName.set(this.auth.getUserName());
      this.userEmail.set(this.auth.getUserEmail());
      if (!loggedIn) {
        this.userMenuOpen.set(false);
        this.notificationsOpen.set(false);
      }
    });
  }

  toggleUserMenu(event?: MouseEvent): void {
    event?.stopPropagation();
    this.userMenuOpen.set(!this.userMenuOpen());
    if (this.userMenuOpen()) this.notificationsOpen.set(false);
  }

  toggleNotifications(event?: MouseEvent): void {
    event?.stopPropagation();
    this.notificationsOpen.set(!this.notificationsOpen());
    if (this.notificationsOpen()) this.userMenuOpen.set(false);
  }

  closeNotifications(): void {
    this.notificationsOpen.set(false);
  }

  setNotifTab(tab: NotifTab, event?: MouseEvent): void {
    event?.stopPropagation();
    this.notifTab.set(tab);
  }

  markAsRead(id: number, event?: MouseEvent): void {
    event?.stopPropagation();
    this.notifications.update((list) => list.map((n) => (n.id === id ? { ...n, read: true } : n)));
  }

  toggleSaved(id: number, event?: MouseEvent): void {
    event?.stopPropagation();
    this.notifications.update((list) =>
      list.map((n) => (n.id === id ? { ...n, saved: !n.saved } : n)),
    );
  }

  iconForKind(kind: NotifKind): string {
    switch (kind) {
      case 'match':
        return 'work';
      case 'reminder':
        return 'tips_and_updates';
      case 'system':
        return 'info';
    }
  }

  @HostListener('document:click')
  closeUserMenu(): void {
    // Solo cerramos el dropdown del avatar — el drawer de notificaciones
    // tiene su propio backdrop y se cierra con su botón explícito.
    if (this.userMenuOpen()) this.userMenuOpen.set(false);
  }

  logout(): void {
    this.auth.logout();
    this.userMenuOpen.set(false);
    this.notificationsOpen.set(false);
    this.router.navigate(['/']);
  }
}

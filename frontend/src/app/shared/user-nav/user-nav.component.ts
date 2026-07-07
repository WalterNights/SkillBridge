import { CommonModule } from '@angular/common';
import { Component, DestroyRef, HostListener, computed, effect, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { Router, RouterModule } from '@angular/router';
import { AuthService } from '../../auth/auth.service';
import {
  NotificationDto,
  NotificationKind,
  NotificationService,
  NotificationTab,
} from '../../services/notification.service';

/**
 * User chrome compartido: campanita + avatar dropdown.
 *
 * El bell abre un drawer lateral derecho con tres pestañas
 * (No leídas / Leídas / Guardadas). El dot rojo en el bell aparece
 * solo cuando hay al menos una notif no leída.
 *
 * Datos reales via `NotificationService` — el modelo de backend (kind,
 * is_read, is_saved, created_at) viaja casi 1:1 a la UI. El timestamp
 * se renderiza con `Intl.RelativeTimeFormat` (built-in del browser, sin
 * libreria) para "hace 1 hora", "hace 3 días", etc.
 */

const _RELATIVE_FMT = new Intl.RelativeTimeFormat('es', { numeric: 'auto' });

function formatRelative(iso: string): string {
  if (!iso) return '';
  const then = new Date(iso).getTime();
  if (Number.isNaN(then)) return '';
  const diffMs = then - Date.now();
  const diffSec = Math.round(diffMs / 1000);
  const absSec = Math.abs(diffSec);
  // Escalado por unidad — el threshold es generoso, no exacto. Para el
  // drawer la precisión absoluta no importa.
  if (absSec < 60) return _RELATIVE_FMT.format(Math.round(diffSec), 'second');
  if (absSec < 3600) return _RELATIVE_FMT.format(Math.round(diffSec / 60), 'minute');
  if (absSec < 86400) return _RELATIVE_FMT.format(Math.round(diffSec / 3600), 'hour');
  if (absSec < 2592000) return _RELATIVE_FMT.format(Math.round(diffSec / 86400), 'day');
  if (absSec < 31536000) return _RELATIVE_FMT.format(Math.round(diffSec / 2592000), 'month');
  return _RELATIVE_FMT.format(Math.round(diffSec / 31536000), 'year');
}

interface UiNotification {
  id: number;
  kind: NotificationKind;
  title: string;
  body: string;
  createdAt: string; // string ya formateado para el template
  read: boolean;
  saved: boolean;
  /** IDs de ofertas asociadas (notif kind=match del cron). Cuando existe
   *  y no está vacío, la card se vuelve clickable — lleva al feed
   *  filtrado por esas ofertas específicas. */
  offerIds?: number[];
}

function toUi(dto: NotificationDto): UiNotification {
  // metadata.offer_ids viene del cron `daily_scrape_for_active_users` en
  // el backend (jobs/tasks.py). Extraemos defensivamente por si el shape
  // cambia — solo aceptamos array de numbers, sino queda undefined.
  const rawIds = (dto.metadata as { offer_ids?: unknown }).offer_ids;
  const offerIds = Array.isArray(rawIds)
    ? rawIds.filter((x): x is number => typeof x === 'number' && Number.isFinite(x))
    : undefined;
  return {
    id: dto.id,
    kind: dto.kind,
    title: dto.title,
    body: dto.body,
    createdAt: formatRelative(dto.created_at),
    read: dto.is_read,
    saved: dto.is_saved,
    offerIds: offerIds && offerIds.length > 0 ? offerIds : undefined,
  };
}

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
  private notifApi = inject(NotificationService);

  isLoggedIn = signal(this.auth.isAuthenticated());
  userMenuOpen = signal(false);
  notificationsOpen = signal(false);
  notifTab = signal<NotificationTab>('unread');

  userName = signal(this.auth.getUserName());
  userEmail = signal(this.auth.getUserEmail());
  userPhotoUrl = signal(this.auth.getProfilePhotoUrl());
  userInitial = computed(() => this.userName().charAt(0).toUpperCase() || 'U');

  notifications = signal<UiNotification[]>([]);
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
      this.userPhotoUrl.set(this.auth.getProfilePhotoUrl());
      if (!loggedIn) {
        this.userMenuOpen.set(false);
        this.notificationsOpen.set(false);
        this.notifications.set([]);
      } else {
        // Carga inicial al loguearse — el bell muestra el dot apenas hay
        // notifs sin necesidad de abrir el drawer.
        this.refresh();
      }
    });

    // Re-fetch cada vez que el drawer pasa a open. Suficiente por
    // ahora — sin polling, sin SSE. El user abre el bell, ve lo último.
    effect(() => {
      if (this.notificationsOpen() && this.isLoggedIn()) {
        this.refresh();
      }
    });
  }

  private refresh(): void {
    this.notifApi.list().subscribe({
      next: (list) => this.notifications.set(list.map(toUi)),
      error: (err) => {
        // Soft-fail: si el backend tira 401/500 no rompemos el chrome.
        // Solo logueamos, el drawer queda vacío.
        console.warn('Failed to load notifications', err);
      },
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

  setNotifTab(tab: NotificationTab, event?: MouseEvent): void {
    event?.stopPropagation();
    this.notifTab.set(tab);
  }

  markAsRead(id: number, event?: MouseEvent): void {
    event?.stopPropagation();
    // Optimistic update — flip el flag local y reverse on error. Hace
    // la UX instantánea y el roundtrip a backend transparente.
    this.notifications.update((list) =>
      list.map((n) => (n.id === id ? { ...n, read: true } : n)),
    );
    this.notifApi.markRead(id).subscribe({
      error: () => {
        this.notifications.update((list) =>
          list.map((n) => (n.id === id ? { ...n, read: false } : n)),
        );
      },
    });
  }

  toggleSaved(id: number, event?: MouseEvent): void {
    event?.stopPropagation();
    const previous = this.notifications().find((n) => n.id === id)?.saved ?? false;
    this.notifications.update((list) =>
      list.map((n) => (n.id === id ? { ...n, saved: !n.saved } : n)),
    );
    this.notifApi.toggleSave(id).subscribe({
      error: () => {
        this.notifications.update((list) =>
          list.map((n) => (n.id === id ? { ...n, saved: previous } : n)),
        );
      },
    });
  }

  iconForKind(kind: NotificationKind): string {
    switch (kind) {
      case 'match':
        return 'work';
      case 'reminder':
        return 'tips_and_updates';
      case 'system':
        return 'info';
    }
  }

  /** Handler al clickear la card de notificación. Si tiene offerIds
   *  (kind=match del cron diario), navega al feed filtrado por esas
   *  ofertas específicas y marca la notif como leída de una. Sin
   *  offerIds no hace nada (evita cambios visuales sin propósito). */
  openNotification(n: UiNotification, event: MouseEvent): void {
    // Ignorar clicks en botones internos ("Marcar como leída", "Guardar")
    // que ya paran propagación — este handler solo actúa cuando el usuario
    // clickea el body de la card.
    const target = event.target as HTMLElement;
    if (target.closest('button')) return;
    if (!n.offerIds || n.offerIds.length === 0) return;

    // Marcar como leída de forma optimista y cerrar el drawer antes de
    // navegar — evita el flicker del drawer cerrándose después del
    // routing.
    if (!n.read) {
      this.markAsRead(n.id);
    }
    this.notificationsOpen.set(false);
    this.router.navigate(['/dashboard'], {
      queryParams: { offer_ids: n.offerIds.join(',') },
    });
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

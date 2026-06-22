import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { Title } from '@angular/platform-browser';
import { AuthService } from '../../auth/auth.service';
import { StorageMethodComponent } from '../../shared/storage-method/storage-method';

/**
 * Configuración del usuario. Vive dentro del AppShell así que el
 * componente solo renderiza contenido — el sidebar y topbar los
 * provee el shell padre.
 *
 * Política dark-only: ya no exponemos toggle de modo claro. Toda la
 * UI vive en el canvas oscuro y los toggles legacy fueron removidos
 * para evitar arrastrar un modo que ya no soportamos.
 */
@Component({
  selector: 'app-settings',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './settings.component.html',
  styleUrls: ['./settings.component.scss'],
})
export class SettingsComponent implements OnInit {
  private router = inject(Router);
  private authService = inject(AuthService);
  private storageMethod = inject(StorageMethodComponent);
  private titleService = inject(Title);

  userName: string | null = null;
  userEmail: string | null = null;
  storage: 'session' | 'local' = 'session';

  enableNotifications = true;
  enableEmailAlerts = false;
  language = 'es';

  constructor() {
    this.titleService.setTitle('SkilTak — Configuración');
  }

  ngOnInit(): void {
    this.storage = localStorage.getItem('storage') === 'true' ? 'local' : 'session';
    this.authService.isLoggedIn$.subscribe(() => {
      this.userName = this.storageMethod.getStorageItem(this.storage, 'user_name');
      this.userEmail = this.storageMethod.getStorageItem(this.storage, 'user_email');
    });
  }

  saveSettings(): void {
    // TODO: persistir las preferencias en backend cuando exista el endpoint.
  }

  goBack(): void {
    this.router.navigate(['/dashboard']);
  }
}

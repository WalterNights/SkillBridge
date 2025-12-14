import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { AuthService } from '../../auth/auth.service';
import { StorageMethodComponent } from '../../shared/storage-method/storage-method';
import { HeaderDashboardComponent } from '../header-dashboard/header-dashboard.component';
import { SidebarComponent } from '../sidebar/sidebar.component';
import { SidebarService } from '../services/sidebar.service';

@Component({
  selector: 'app-settings',
  standalone: true,
  imports: [CommonModule, FormsModule, HeaderDashboardComponent, SidebarComponent],
  templateUrl: './settings.component.html',
  styleUrls: ['./settings.component.scss']
})
export class SettingsComponent {
  userName: string | null = null;
  userEmail: string | null = null;
  storage: 'session' | 'local' = 'session';
  isDarkMode = false;
  enableNotifications = true;
  enableEmailAlerts = false;
  language = 'es';
  isSidebarCollapsed = false;

  constructor(
    private router: Router,
    private authService: AuthService,
    private storageMethod: StorageMethodComponent,
    private sidebarService: SidebarService,
  ) {}

  ngOnInit(): void {
    this.storage = localStorage.getItem('storage') === 'true' ? 'local' : 'session';
    this.authService.isLoggedIn$.subscribe(status => {
      this.userName = this.storageMethod.getStorageItem(this.storage, 'user_name');
      this.userEmail = this.storageMethod.getStorageItem(this.storage, 'user_email');
    });

    // Load theme preference
    const saveTheme = localStorage.getItem('theme');
    this.isDarkMode = saveTheme === 'dark';

    // Subscribe to sidebar state changes
    this.sidebarService.isCollapsed$.subscribe(collapsed => {
      this.isSidebarCollapsed = collapsed;
    });
  }

  toggleDarkMode(): void {
    this.isDarkMode = !this.isDarkMode;
    const root = document.documentElement;
    if (this.isDarkMode) {
      root.classList.add('dark');
      localStorage.setItem('theme', 'dark');
    } else {
      root.classList.remove('dark');
      localStorage.setItem('theme', 'light');
    }
  }

  saveSettings(): void {
    // Aquí puedes agregar lógica para guardar las configuraciones en el backend
    console.log('Settings saved:', {
      enableNotifications: this.enableNotifications,
      enableEmailAlerts: this.enableEmailAlerts,
      language: this.language
    });
  }

  goBack(): void {
    this.router.navigate(['/dashboard']);
  }
}

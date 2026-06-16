import { Router } from '@angular/router';
import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { AuthService } from '../../auth/auth.service';
import { StorageMethodComponent } from '../../shared/storage-method/storage-method';
import { SidebarService } from '../services/sidebar.service';

@Component({
  selector: 'app-header-dashboard',
  imports: [CommonModule],
  standalone: true,
  templateUrl: './header-dashboard.component.html',
  styleUrls: ['./header-dashboard.component.scss']
})
export class HeaderDashboardComponent {
  users: any;
  isLoading = false;
  userName: string | null = null;
  isLoggedIn: boolean = false;
  isDarkMode = false;
  isSidebarCollapsed = false;
  storage: 'session' | 'local' = 'session';

  constructor(
    private router: Router,
    private authService: AuthService,
    private storageMethod: StorageMethodComponent,
    private sidebarService: SidebarService,
  ) { }

  ngOnInit(): void {
    this.storage = localStorage.getItem('storage') === 'true' ? 'local' : 'session';
    this.authService.isLoggedIn$.subscribe(status => {
      this.isLoggedIn = status;
      this.userName = this.storageMethod.getStorageItem(this.storage, 'user_name');
    })

    // Load dark mode preference
    const saveTheme = localStorage.getItem('theme');
    if (saveTheme === 'dark') {
      this.isDarkMode = true;
      document.documentElement.classList.add('dark');
    }

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

  navigateTo(route: string): void {
    this.router.navigate([route]);
  }

  logout(): void {
    this.isLoading = true;
    this.authService.logout();
    this.authService.updateProfileStatus();
    setTimeout(() => {
      this.isLoading = false;
      this.router.navigate(['/']);
    }, 1200);
  }

}

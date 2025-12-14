import { Router } from '@angular/router';
import { Component, EventEmitter, Output } from '@angular/core';
import { CommonModule } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { AuthService } from '../../auth/auth.service';
import { environment } from '../../../environment/environment';
import { StorageMethodComponent } from '../../shared/storage-method/storage-method';
import { SidebarService } from '../services/sidebar.service';

@Component({
  selector: 'app-sidebar',
  imports: [CommonModule],
  standalone: true,
  templateUrl: './sidebar.component.html',
  styleUrls: ['./sidebar.component.scss']
})
export class SidebarComponent {
  isCollapsed = false;
  userName: string | null = null;
  storage: 'session' | 'local' = 'session';

  constructor(
    private router: Router,
    private http: HttpClient,
    private authService: AuthService,
    private storageMethod: StorageMethodComponent,
    private sidebarService: SidebarService,
  ){}

  ngOnInit(): void {
    this.storage = localStorage.getItem('storage') === 'true' ? 'local' : 'session';
    this.authService.isLoggedIn$.subscribe(status => {
      this.userName = this.storageMethod.getStorageItem(this.storage, 'user_name');
    });

    // Subscribe to sidebar state changes
    this.sidebarService.isCollapsed$.subscribe(collapsed => {
      this.isCollapsed = collapsed;
    });
  }

  toggleSidebar(): void {
    this.sidebarService.toggleSidebar();
  }

  navigateTo(route: string): void {
    this.router.navigate([route]);
  }

}

import { Router } from '@angular/router';
import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { environment } from '../../environment/environment';
import { User } from '../models/user.model';
import { HeaderDashboardComponent } from './header-dashboard/header-dashboard.component';
import { SidebarComponent } from './sidebar/sidebar.component';
import { SidebarService } from './services/sidebar.service';

/**
 * Dashboard component for user management
 */
@Component({
  selector: 'app-dashboard',
  imports: [CommonModule, HeaderDashboardComponent, SidebarComponent],
  standalone: true,
  templateUrl: './dashboard.component.html',
  styleUrls: ['./dashboard.component.scss']
})
export class DashboardComponent {
  users: User[] = [];
  isLoading = false;
  errorMessage = '';
  isSidebarCollapsed = false;

  constructor(
    private router: Router,
    private http: HttpClient,
    private sidebarService: SidebarService,
  ){}

  /**
   * Initializes component and loads user data
   */
  ngOnInit(): void {
    this.loadUsers();

    // Subscribe to sidebar state changes
    this.sidebarService.isCollapsed$.subscribe(collapsed => {
      this.isSidebarCollapsed = collapsed;
    });
  }

  /**
   * Loads users from the API
   */
  private loadUsers(): void {
    this.isLoading = true;
    this.http.get<User[]>(`${environment.apiUrl}/dashboard/`).subscribe({
      next: (data) => {
        this.users = data;
        this.isLoading = false;
      },
      error: (err: HttpErrorResponse) => {
        console.error('Failed to load users:', err);
        this.errorMessage = 'Error al cargar usuarios';
        this.users = [];
        this.isLoading = false;
      }
    });
  }
}

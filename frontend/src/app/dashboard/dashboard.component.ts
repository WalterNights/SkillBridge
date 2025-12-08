import { Router } from '@angular/router';
import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { environment } from '../../environment/environment';
import { User } from '../models/user.model';

/**
 * Dashboard component for user management
 */
@Component({
  selector: 'app-dashboard',
  imports: [CommonModule],
  standalone: true,
  templateUrl: './dashboard.component.html',
  styleUrls: ['./dashboard.component.scss']
})
export class DashboardComponent {
  users: User[] = [];
  isLoading = false;
  errorMessage = '';

  constructor(
    private router: Router,
    private http: HttpClient,
  ){}

  /**
   * Initializes component and loads user data
   */
  ngOnInit(): void {
    this.loadUsers();
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

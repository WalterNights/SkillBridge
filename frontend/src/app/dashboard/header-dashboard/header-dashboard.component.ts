import { Router } from '@angular/router';
import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { AuthService } from '../../auth/auth.service';
import { environment } from '../../../environment/environment';
import { StorageMethodComponent } from '../../shared/storage-method/storage-method';

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
  storage: 'session' | 'local' = 'session';

  constructor(
    private router: Router,
    private http: HttpClient,
    private authService: AuthService,
    private storageMethod: StorageMethodComponent,
  ) { }

  ngOnInit(): void {
    this.storage = localStorage.getItem('storage') === 'true' ? 'local' : 'session';
    this.authService.isLoggedIn$.subscribe(status => {
      this.isLoggedIn = status;
      this.userName = this.storageMethod.getStorageItem(this.storage, 'user_name');
    })
  }

  logout() {
    this.isLoading = true;
    this.authService.logout();
    this.authService.updateProfileStatus();
    setTimeout(() => {
      this.isLoading = false;
      this.router.navigate(['/']);
    }, 1200);
  }

}
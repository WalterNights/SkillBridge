import { Router } from '@angular/router';
import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Title } from '@angular/platform-browser';
import { AuthService } from '../auth/auth.service';
import { STORAGE_KEYS } from '../constants/app-stats';

/**
 * Home/Landing page component
 */
@Component({
  selector: 'app-home',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './home.component.html',
  styleUrls: ['./home.component.scss']
})
export class HomeComponent {
  profileComplete = false;

  constructor(
    private titleService: Title,
    private authService: AuthService,
    private router: Router
  ) {
    this.titleService.setTitle('SkillBridge - Home');
  }

  /**
   * Navigates to manual profile page, redirecting to login if not authenticated
   */
  goToManualProfile(): void {
    if (!this.authService.isAuthenticated()){
      sessionStorage.setItem(STORAGE_KEYS.REDIRECT_AFTER_LOGIN, '/manual-profile');
      this.router.navigate(['/auth/login']);
    } else {
      this.router.navigate(['/manual-profile']);
    }
  }

  /**
   * Navigates to profile page, redirecting to login if not authenticated
   */
  goToProfile(): void {
    if (!this.authService.isAuthenticated()){
      sessionStorage.setItem(STORAGE_KEYS.REDIRECT_AFTER_LOGIN, '/profile');
      this.router.navigate(['/auth/login']);
    } else {
      this.router.navigate(['/profile']);
    }
  }

  /**
   * Navigates to results page, redirecting to login if not authenticated
   */
  goToResults(): void {
    if (!this.authService.isAuthenticated()){
      sessionStorage.setItem(STORAGE_KEYS.REDIRECT_AFTER_LOGIN, '/results');
      this.router.navigate(['/auth/login']);
    } else {
      this.router.navigate(['/results']);
    }
  }

  ngOnInit(): void {
    this.authService.isProfileComplete$.subscribe(status => {
      this.profileComplete = status;
    })
  }
}

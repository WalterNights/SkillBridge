import { Router } from '@angular/router';
import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Title } from '@angular/platform-browser';
import { AuthService } from '../auth/auth.service';

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

  goToManualProfile() {
    if (!this.authService.isAuthenticated()){
      sessionStorage.setItem('redirect_after_login', '/manual-profile');
      this.router.navigate(['/auth/login']);
    } else {
      this.router.navigate(['/manual-profile']);
    }
  }

  goToProfile() {
    if (!this.authService.isAuthenticated()){
      sessionStorage.setItem('redirect_after_login', '/profile');
      this.router.navigate(['/auth/login']);
    } else {
      this.router.navigate(['/profile']);
    }
  }

  goToResults() {
    if (!this.authService.isAuthenticated()){
      sessionStorage.setItem('redirect_after_login', '/results');
      this.router.navigate(['/auth/login']);
    } else {
      this.router.navigate(['/results']);
    }
  }

  ngOnInit() {
    this.authService.isProfileComplete$.subscribe(status => {
      this.profileComplete = status;
    })
  }

}

import { Router } from '@angular/router';
import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { AuthService } from '../auth/auth.service';

@Component({
   selector: 'app-header',
   standalone: true,
   imports: [CommonModule],
   templateUrl: './header.component.html',
   styleUrls: ['./header.component.scss']
})
export class HeaderComponent {
   isDarkMode = false;
   isLoggedIn = false;
   isLoading = false;

   constructor(private router: Router,private authService: AuthService) {}
   toggleDarkMode() {
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

   goToHome() {
      this.router.navigate(['/'])
   }

   login() {
      this.router.navigate(['auth/login']);
   }

   logout() {
      this.isLoading = true;
      setTimeout(() => {
          this.isLoading = false;
          this.isLoggedIn = false;
          this.router.navigate(['/']);
      }, 1200);
   }

   ngOnInit() {
      this.authService.isLoggedIn$.subscribe(status => {
         this.isLoggedIn = status;
      })
      const saveTheme = localStorage.getItem('theme');
      if (saveTheme === 'dark') {
         this.isDarkMode = true;
         document.documentElement.classList.add('dark');
      }
   }
}

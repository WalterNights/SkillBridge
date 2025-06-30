import { Router } from '@angular/router';
import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';

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

   constructor(private router: Router) { }
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

   login() {
      this.router.navigate(['auth/login']);
   }

   logout() {
      // Aquí deberías llamar a tu AuthService
      this.isLoggedIn = false;
      this.router.navigate(['/']);
   }

   ngOnInit() {
      const saveTheme = localStorage.getItem('theme');
      if (saveTheme === 'dark') {
         this.isDarkMode = true;
         document.documentElement.classList.add('dark');
      }
   }
}

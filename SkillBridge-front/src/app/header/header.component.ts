import { Router } from '@angular/router';
import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { AuthService } from '../auth/auth.service';
import { StorageMethodComponent } from '../shared/storage-method/storage-method';

@Component({
   selector: 'app-header',
   standalone: true,
   imports: [CommonModule],
   templateUrl: './header.component.html',
   styleUrls: ['./header.component.scss']
})
export class HeaderComponent {
   userName: string | null = null;
   isDarkMode = false;
   isLoggedIn: boolean = false;
   isLoading = false;
   storage: 'session' | 'local' = 'session';

   constructor(private router: Router,private authService: AuthService, private storageMethod: StorageMethodComponent) {}
   
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
      this.router.navigate(['/']).then(() => {
         this.authService.updateProfileStatus();
      });
   }

   login() {
      this.isLoading = true;
      setTimeout(() => {
          this.isLoading = false;
          this.router.navigate(['auth/login']);
      }, 1200);
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

   ngOnInit() {
      this.storage = localStorage.getItem('storage') === 'true' ? 'local' : 'session';
      this.authService.isLoggedIn$.subscribe(status => {
         this.isLoggedIn = status;
         this.userName = this.storageMethod.getStorageItem(this.storage, 'user_name');
      })
      const saveTheme = localStorage.getItem('theme');
      if (saveTheme === 'dark') {
         this.isDarkMode = true;
         document.documentElement.classList.add('dark');
      }
   }
}

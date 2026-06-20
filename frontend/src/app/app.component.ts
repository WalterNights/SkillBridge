import { filter } from 'rxjs';
import { CommonModule } from '@angular/common';
import { AuthService } from './auth/auth.service';
import { HeaderComponent } from './header/header.component';
import { initMaterialTailwind } from '@material-tailwind/html';
import { Component, OnInit, AfterViewInit } from '@angular/core';
import { Router, RouterOutlet, NavigationEnd } from '@angular/router';
import { SidebarComponent } from './dashboard/sidebar/sidebar.component';
import { HeaderDashboardComponent } from './dashboard/header-dashboard/header-dashboard.component';
import { ToastContainerComponent } from './shared/molecules/toast-container/toast-container.component';

@Component({
  selector: 'app-root',
  imports: [
    CommonModule,
    RouterOutlet,
    HeaderComponent,
    SidebarComponent,
    HeaderDashboardComponent,
    ToastContainerComponent,
  ],
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.scss'],
})
export class AppComponent implements AfterViewInit, OnInit {
  title = 'SkilTak-front';
  showHeader = true;
  showSideBar = true;
  showHeaderDashboard = true;
  constructor(
    private authService: AuthService,
    private router: Router,
  ) {
    this.router.events
      .pipe(filter((event) => event instanceof NavigationEnd))
      .subscribe((event: any) => {
        // El landing nuevo (/) trae su propio navbar, no usar el legacy.
        // /auth/login y /dashboard tampoco usan el header público.
        // Los demás (resto de /auth/*, /jobs/:id, /profile, /cv, etc)
        // van a perder el header legacy a medida que portemos cada uno.
        const noHeader = ['/', '/auth/login', '/dashboard'];
        const sideBar = ['/dashboard'];
        const headerDashboard = ['/dashboard'];
        this.showHeader = !noHeader.includes(event.urlAfterRedirects);
        this.showSideBar = sideBar.includes(event.urlAfterRedirects);
        this.showHeaderDashboard = headerDashboard.includes(event.urlAfterRedirects);
      });
  }
  ngOnInit(): void {
    this.authService.syncAuthStatus();
  }
  ngAfterViewInit(): void {
    // initMaterialTailwind(); // Comentado: causa errores con dropdowns que no existen
  }
}

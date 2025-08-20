import { filter } from 'rxjs';
import { CommonModule } from '@angular/common';
import { AuthService } from './auth/auth.service';
import { HeaderComponent } from './header/header.component';
import { initMaterialTailwind } from '@material-tailwind/html';
import { Component, OnInit, AfterViewInit } from '@angular/core';
import { Router, RouterOutlet, NavigationEnd } from '@angular/router';
import { SidebarComponent } from './dashboard/sidebar/sidebar.component';
import { HeaderDashboardComponent } from './dashboard/header-dashboard/header-dashboard.component';

@Component({
  selector: 'app-root',
  imports: [CommonModule, RouterOutlet, HeaderComponent, SidebarComponent, HeaderDashboardComponent],
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.scss']
})
export class AppComponent implements AfterViewInit, OnInit {
  title = 'SkillBridge-front';
  showHeader = true;
  showSideBar = true;
  showHeaderDashboard = true;
  constructor(
    private authService: AuthService,
    private router: Router
  ){
    this.router.events
    .pipe(filter(event => event instanceof NavigationEnd))
    .subscribe((event: any) => {
      const noHeader = ['auth/login', '/dashboard'];
      const SideBar = ['/dashboard'];
      const showHeaderDashboard = ['/dashboard'];
      this.showHeader = !noHeader.includes(event.urlAfterRedirects);
      this.showSideBar = SideBar.includes(event.urlAfterRedirects);
      this.showSideBar = showHeaderDashboard.includes(event.urlAfterRedirects);
    })
  }
  ngOnInit(): void {
    this.authService.syncAuthStatus();
  }
  ngAfterViewInit(): void {
    initMaterialTailwind();
  }
}
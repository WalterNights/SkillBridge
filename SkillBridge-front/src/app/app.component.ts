import { RouterOutlet } from '@angular/router';
import { AuthService } from './auth/auth.service';
import { HeaderComponent } from './header/header.component';
import { initMaterialTailwind } from '@material-tailwind/html';
import { Component, OnInit, AfterViewInit } from '@angular/core';

@Component({
  selector: 'app-root',
  imports: [RouterOutlet, HeaderComponent],
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.scss']
})
export class AppComponent implements AfterViewInit, OnInit {
  title = 'SkillBridge-front';
  constructor(private authService: AuthService){}
  ngOnInit(): void {
    this.authService.syncAuthStatus();
  }
  ngAfterViewInit(): void {
    initMaterialTailwind();
  }
}
import { Router } from '@angular/router';
import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Title } from '@angular/platform-browser';

@Component({
  selector: 'app-home',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './home.component.html',
  styleUrls: ['./home.component.scss']
})
export class HomeComponent {
  constructor(
    private titleService: Title,
    private router: Router
  ) {
    this.titleService.setTitle('SkillBridge - Home');
  }

  goToResults() {
    this.router.navigate(['/results']);
  }

}

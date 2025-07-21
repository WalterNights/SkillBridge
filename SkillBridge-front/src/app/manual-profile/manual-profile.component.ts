import { Router } from '@angular/router';
import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Title } from '@angular/platform-browser';

@Component({
  selector: 'app-manual-profile',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './manual-profile.component.html',
  styleUrls: ['./manual-profile.component.scss']
})
export class ManualProfileComponent {

  constructor(
    private titleService: Title,
    private router: Router
  ) {
    this.titleService.setTitle('SkillBridge - Registro Perfil Profesional');
  }

}

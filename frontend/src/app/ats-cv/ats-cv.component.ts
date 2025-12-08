import { jsPDF } from 'jspdf';
import html2canvas from 'html2canvas';
import { Router } from '@angular/router';
import { CommonModule } from '@angular/common';
import localeEs from '@angular/common/locales/es';
import { AuthService } from '../auth/auth.service';
import { Title } from '@angular/platform-browser';
import { registerLocaleData } from '@angular/common';
import { Component, OnInit, ViewChild, ElementRef } from '@angular/core';


@Component({
  selector: 'app-ats-cv',
  imports: [CommonModule],
  standalone: true,
  templateUrl: './ats-cv.component.html',
  styleUrls: ['./ats-cv.component.scss']
})
export class AtsCvComponent implements OnInit {
  userEmail: string | null = null;
  profileData: any = null;
  @ViewChild('cvContent', { static: false }) cvContent!: ElementRef;

  constructor(
    private titleService: Title,
    private authService: AuthService,
    private router: Router
  ) {
    this.titleService.setTitle('SkilTak - Resultados');
  }

  ngOnInit(): void {
    registerLocaleData(localeEs, 'es');
    const savedData = localStorage.getItem('manual_profile_draft');
    this.userEmail = sessionStorage.getItem('user_email');
    this.profileData = savedData ? JSON.parse(savedData) : null;
  }

  downloadCV(): void {
    const element = this.cvContent.nativeElement;
    const doc = new jsPDF('p', 'pt', 'a4');
    if (element) {
      doc.html(element, {
        callback: (doc) => {
          doc.save('skiltak-ats-cv.pdf');
          //this.router.navigate(['/results']);
        },
        x: 10,
        y: 0,
        html2canvas: {scale: 0.65}
      });
      //localStorage.removeItem('manual_profile_draft');
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
}
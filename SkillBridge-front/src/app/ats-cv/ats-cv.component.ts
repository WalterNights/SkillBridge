import { jsPDF } from 'jspdf';
import html2pdf from 'html2pdf.js';
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
  profileData: any = null;
  @ViewChild('cvContent', { static: false }) cvContent!: ElementRef;

  constructor(
    private titleService: Title,
    private authService: AuthService,
    private router: Router
  ) {
    this.titleService.setTitle('SkillBridge - Resultados');
  }

  ngOnInit(): void {
    registerLocaleData(localeEs, 'es');
    const savedData = localStorage.getItem('manual_profile_draft');
    this.profileData = savedData ? JSON.parse(savedData) : null;
  }

  downloadCV(): void {
    const element = this.cvContent.nativeElement;
    html2canvas(element, {
      scale: 2,
      useCORS: true
    }).then(canvas => {
      const imgData = canvas.toDataURL('image/png');
      const pdf = new jsPDF('p', 'pt', 'a4');
      const pageWidth = pdf.internal.pageSize.getWidth();
      const pageHeight = pdf.internal.pageSize.getHeight();
      // Force scale to can in on one page
      const imgProps = pdf.getImageProperties(imgData);
      const imgRatio = imgProps.width / imgProps.height;
      const scaledWidth = pageWidth;
      const scaledHeight = pageWidth / imgRatio;
      pdf.addImage(imgData, 'PNG', 0, 0, scaledWidth, scaledHeight);
      pdf.save('skillbridge-ats-cv.pdf');
    });
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
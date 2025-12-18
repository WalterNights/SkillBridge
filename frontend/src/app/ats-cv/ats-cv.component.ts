import { jsPDF } from 'jspdf';
import html2canvas from 'html2canvas';
import { Router } from '@angular/router';
import { CommonModule } from '@angular/common';
import localeEs from '@angular/common/locales/es';
import { AuthService } from '../auth/auth.service';
import { Title } from '@angular/platform-browser';
import { registerLocaleData } from '@angular/common';
import { Component, OnInit, ViewChild, ElementRef } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { environment } from '../../environment/environment';
import { STORAGE_KEYS } from '../constants/app-stats';

@Component({
  selector: 'app-ats-cv',
  imports: [CommonModule],
  standalone: true,
  templateUrl: './ats-cv.component.html',
  styleUrls: ['./ats-cv.component.scss']
})
export class AtsCvComponent implements OnInit {
  profileData: any = null;
  isLoading = true;
  errorMessage = '';
  @ViewChild('cvContent', { static: false }) cvContent!: ElementRef;

  constructor(
    private titleService: Title,
    private authService: AuthService,
    private router: Router,
    private http: HttpClient
  ) {
    this.titleService.setTitle('SkilTak - CV ATS');
  }

  ngOnInit(): void {
    registerLocaleData(localeEs, 'es');
    this.loadProfileData();
  }

  /**
   * Load profile data from localStorage first, then optionally from backend
   */
  loadProfileData(): void {
    // First try to get from localStorage (most recent form data)
    const savedData = localStorage.getItem(STORAGE_KEYS.MANUAL_PROFILE_DRAFT);
    if (savedData) {
      try {
        this.profileData = JSON.parse(savedData);
        console.log('📋 Datos cargados desde localStorage:', this.profileData);
        console.log('✅ Education type:', typeof this.profileData.education, Array.isArray(this.profileData.education) ? `(array of ${this.profileData.education.length})` : '');
        console.log('✅ Experience type:', typeof this.profileData.experience, Array.isArray(this.profileData.experience) ? `(array of ${this.profileData.experience.length})` : '');

        if (Array.isArray(this.profileData.education) && this.profileData.education.length > 0) {
          console.log('📚 First education entry:', this.profileData.education[0]);
        }
        if (Array.isArray(this.profileData.experience) && this.profileData.experience.length > 0) {
          console.log('💼 First experience entry:', this.profileData.experience[0]);
        }

        // Si no tiene email, intentar obtenerlo del usuario autenticado
        if (!this.profileData.email) {
          const userEmail = sessionStorage.getItem('user_email');
          if (userEmail) {
            this.profileData.email = userEmail;
          }
        }
      } catch (e) {
        console.error('❌ Error parsing localStorage data:', e);
        this.fetchProfileFromBackend();
        return;
      }

      this.isLoading = false;
    } else {
      console.log('⚠️ No hay datos en localStorage, consultando backend...');
      // If no localStorage data, fetch from backend
      this.fetchProfileFromBackend();
    }
  }

  /**
   * Fetch profile data from backend
   */
  fetchProfileFromBackend(): void {
    const token = localStorage.getItem(STORAGE_KEYS.ACCESS_TOKEN);
    if (!token) {
      this.errorMessage = 'No se encontraron datos del perfil';
      this.isLoading = false;
      return;
    }

    const headers = new HttpHeaders({ Authorization: `Bearer ${token}` });
    this.http.get<any>(`${environment.apiUrl}/users/profiles/`, { headers }).subscribe({
      next: (response) => {
        // API returns array, get first profile
        const profile = Array.isArray(response) ? response[0] : response;
        if (profile) {
          this.profileData = this.formatProfileData(profile);
        }
        this.isLoading = false;
      },
      error: (err) => {
        console.error('Error loading profile:', err);
        this.errorMessage = 'Error al cargar el perfil';
        this.isLoading = false;
      }
    });
  }

  /**
   * Format backend profile data to match expected structure
   */
  formatProfileData(profile: any): any {
    return {
      first_name: profile.first_name || '',
      last_name: profile.last_name || '',
      email: profile.user?.email || profile.email || '',
      number_id: profile.number_id || '',
      phone_code: profile.phone_code || '',
      phone_number: profile.phone_number || profile.phone || '',
      city: profile.city || '',
      country: profile.country || '',
      professional_title: profile.professional_title || '',
      summary: profile.summary || '',
      linkedin_url: profile.linkedin_url || '',
      portfolio_url: profile.portfolio_url || '',
      skills: profile.skills || '',
      experience: this.parseTextToArray(profile.experience),
      education: this.parseTextToArray(profile.education)
    };
  }

  /**
   * Parse text-based experience/education to array format if needed
   */
  parseTextToArray(text: string | any[]): any[] {
    if (Array.isArray(text)) return text;
    if (!text) return [];
    // If it's a string, try to parse it or return empty
    return [];
  }

  downloadCV(): void {
    const element = this.cvContent.nativeElement;
    if (!element) return;

    // A4 dimensions in points (1 inch = 72 points, A4 = 210mm x 297mm)
    const a4Width = 595.28;
    const a4Height = 841.89;

    html2canvas(element, {
      scale: 2,
      useCORS: true,
      logging: false,
      backgroundColor: '#ffffff'
    }).then((canvas) => {
      const imgData = canvas.toDataURL('image/png');
      const doc = new jsPDF('p', 'pt', 'a4');

      const imgWidth = a4Width;
      const imgHeight = (canvas.height * a4Width) / canvas.width;

      // If content is taller than one page, handle multiple pages
      let heightLeft = imgHeight;
      let position = 0;

      doc.addImage(imgData, 'PNG', 0, position, imgWidth, imgHeight);
      heightLeft -= a4Height;

      while (heightLeft > 0) {
        position = heightLeft - imgHeight;
        doc.addPage();
        doc.addImage(imgData, 'PNG', 0, position, imgWidth, imgHeight);
        heightLeft -= a4Height;
      }

      doc.save('skiltak-ats-cv.pdf');
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

  /**
   * Check if education data is in array format
   */
  isEducationArray(): boolean {
    return Array.isArray(this.profileData?.education) && this.profileData.education.length > 0;
  }

  /**
   * Check if experience data is in array format
   */
  isExperienceArray(): boolean {
    return Array.isArray(this.profileData?.experience) && this.profileData.experience.length > 0;
  }
}

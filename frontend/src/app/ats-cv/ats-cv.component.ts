import { jsPDF } from 'jspdf';
import html2canvas from 'html2canvas';
import { Router, RouterModule } from '@angular/router';
import { CommonModule } from '@angular/common';
import localeEs from '@angular/common/locales/es';
import { AuthService } from '../auth/auth.service';
import { Title } from '@angular/platform-browser';
import { registerLocaleData } from '@angular/common';
import { Component, OnInit, ViewChild, ElementRef, signal } from '@angular/core';
import { ProfileService } from '../services/profile.service';
import { ToastService } from '../services/toast.service';
import { STORAGE_KEYS } from '../constants/app-stats';
import { QuantifyModalComponent } from '../cv/quantify-modal.component';
import { CvAuditModalComponent } from '../cv/cv-audit-modal.component';

@Component({
  selector: 'app-ats-cv',
  imports: [CommonModule, RouterModule, QuantifyModalComponent, CvAuditModalComponent],
  standalone: true,
  templateUrl: './ats-cv.component.html',
  styleUrls: ['./ats-cv.component.scss'],
})
export class AtsCvComponent implements OnInit {
  profileData: any = null;
  isLoading = true;
  errorMessage = '';
  @ViewChild('cvContent', { static: false }) cvContent!: ElementRef;

  /** Cuando está seteado, muestra el modal de cuantificar para esa entry.
   * Guardamos el índice + el snapshot del texto para evitar race conditions
   * si el user clickea otra entry mientras el modal está abierto. */
  quantifyTarget = signal<{ index: number; text: string; role: string; company: string } | null>(
    null,
  );
  /** Flag para ocultar los botones AI cuando se captura el PDF — html2canvas
   * no respeta @media print, así que usamos una clase toggleable. */
  isExporting = signal(false);

  /** Modal del auditor — solo se monta cuando se abre (lazy). */
  showAudit = signal(false);

  openAudit(): void {
    this.showAudit.set(true);
  }

  closeAudit(): void {
    this.showAudit.set(false);
  }

  constructor(
    private titleService: Title,
    private authService: AuthService,
    private router: Router,
    private profileService: ProfileService,
    private toast: ToastService,
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

        // Si no tiene email, intentar obtenerlo del usuario autenticado
        if (!this.profileData.email) {
          const userEmail = sessionStorage.getItem('user_email');
          if (userEmail) {
            this.profileData.email = userEmail;
          }
        }
      } catch (e) {
        console.error('Error parsing localStorage data:', e);
        this.fetchProfileFromBackend();
        return;
      }

      this.isLoading = false;
    } else {
      // No data in localStorage, fetch from backend
      this.fetchProfileFromBackend();
    }
  }

  /**
   * Fetch profile data from backend.
   * El token se inyecta automáticamente por `TokenInterceptor`.
   *
   * Se chequea via AuthService.isAuthenticated() en vez de
   * `localStorage.getItem(ACCESS_TOKEN)` porque el AuthService puede
   * guardar el token en sessionStorage si "remember me" está apagado.
   * Hardcodear localStorage rompía el flow para usuarios que no
   * tildaban remember-me.
   */
  fetchProfileFromBackend(): void {
    if (!this.authService.isAuthenticated()) {
      this.errorMessage = 'No se encontraron datos del perfil';
      this.isLoading = false;
      return;
    }

    this.profileService.getMyProfile().subscribe({
      next: (response) => {
        // El endpoint puede devolver:
        //   - DRF paginated: {count, next, previous, results: [{...}]}
        //   - array crudo (cuando no hay pagination): [{...}]
        //   - objeto puntual (cuando se pide /profiles/{id}/): {...}
        // Cubrimos los tres casos en orden de probabilidad.
        let profile: any = response;
        if (response && Array.isArray(response.results)) {
          profile = response.results[0];
        } else if (Array.isArray(response)) {
          profile = response[0];
        }
        if (profile) {
          this.profileData = this.formatProfileData(profile);
        } else {
          this.errorMessage = 'No se encontraron datos del perfil';
        }
        this.isLoading = false;
      },
      error: (err) => {
        console.error('Error loading profile:', err);
        this.errorMessage = 'Error al cargar el perfil';
        this.isLoading = false;
      },
    });
  }

  /**
   * Format backend profile data to match expected structure
   */
  formatProfileData(profile: any): any {
    return {
      // `id` se mantiene para que PATCH al profile (cuantificar, etc) tenga
      // la URL correcta. Si viene del localStorage draft puede ser undefined.
      id: profile.id ?? null,
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
      experience: this.parseExperienceOrEducation(profile.experience),
      education: this.parseExperienceOrEducation(profile.education),
    };
  }

  /**
   * Normaliza experience/education. El backend los guarda como TextField
   * libre, pero el wizard de Gemini los puebla como JSON parseado a
   * array de objetos. Soportamos los tres casos:
   *   - array de objetos (Gemini): pasa tal cual → el HTML usa ngFor
   *   - JSON string que parsea a array: lo parseamos a array
   *   - string libre: lo devolvemos como string → el HTML cae al
   *     fallback `*ngIf="!isXxxArray()"` que lo renderiza como texto
   *
   * Antes devolvíamos [] para cualquier string, lo que dejaba la
   * sección rota porque el HTML cree que es un array vacío y no
   * dispara el fallback de texto.
   */
  parseExperienceOrEducation(value: string | any[] | null | undefined): string | any[] {
    if (Array.isArray(value)) return value;
    if (!value) return '';
    // Algunos perfiles legacy guardaron el JSON serializado como string.
    const trimmed = value.trim();
    if (trimmed.startsWith('[') || trimmed.startsWith('{')) {
      try {
        const parsed = JSON.parse(trimmed);
        if (Array.isArray(parsed)) return parsed;
      } catch {
        // No es JSON válido — caemos al texto libre.
      }
    }
    return value;
  }

  // ---- Cuantificar logros con AI -----------------------------------

  /** Abre el modal para una entry de experiencia. Solo aplica cuando
   * `isExperienceArray()` es true — los users con experiencia como texto
   * libre no ven el botón (no hay descripción discreta a cuantificar). */
  openQuantify(index: number): void {
    const exp = this.profileData?.experience?.[index];
    if (!exp || !exp.description) return;
    this.quantifyTarget.set({
      index,
      text: exp.description,
      role: exp.position || '',
      company: exp.company || '',
    });
  }

  closeQuantify(): void {
    this.quantifyTarget.set(null);
  }

  /** El modal emitió la sugerencia que el user aceptó. Optimistic update:
   * cambiamos la descripción local + PATCH al backend. Si el PATCH falla,
   * revertimos y avisamos. */
  onQuantifyApplied(newText: string): void {
    const target = this.quantifyTarget();
    if (!target) return;
    const profileId = this.profileData?.id;
    if (!profileId) {
      this.toast.error('No pudimos identificar tu perfil. Recargá la página.');
      return;
    }

    const previousText = this.profileData.experience[target.index].description;
    // Optimistic
    this.profileData.experience[target.index] = {
      ...this.profileData.experience[target.index],
      description: newText,
    };
    this.closeQuantify();

    // El backend guarda `experience` como TextField; serializamos el array
    // a JSON string. Si más adelante migramos a JSONField, ajustar acá.
    const payload = { experience: JSON.stringify(this.profileData.experience) };
    this.profileService.patchProfile(profileId, payload).subscribe({
      next: () => {
        this.toast.success('Logro actualizado en tu CV.');
      },
      error: () => {
        // Rollback
        this.profileData.experience[target.index] = {
          ...this.profileData.experience[target.index],
          description: previousText,
        };
        this.toast.error('No pudimos guardar el cambio. Intentá de nuevo.');
      },
    });
  }

  downloadCV(): void {
    const element = this.cvContent.nativeElement;
    if (!element) return;

    // Ocultamos los botones AI (.no-export) antes de capturar — html2canvas
    // hace screenshot del DOM tal cual, no respeta @media print.
    this.isExporting.set(true);

    // A4 dimensions in points (1 inch = 72 points, A4 = 210mm x 297mm)
    const a4Width = 595.28;
    const a4Height = 841.89;

    html2canvas(element, {
      scale: 2,
      useCORS: true,
      logging: false,
      backgroundColor: '#ffffff',
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
      this.isExporting.set(false);
    }).catch(() => {
      this.isExporting.set(false);
    });
  }

  goToDashboard() {
    if (!this.authService.isAuthenticated()) {
      sessionStorage.setItem('redirect_after_login', '/dashboard');
      this.router.navigate(['/auth/login']);
    } else {
      this.router.navigate(['/dashboard']);
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

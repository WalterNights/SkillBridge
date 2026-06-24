import { jsPDF } from 'jspdf';
import html2canvas from 'html2canvas';
import { Router, RouterModule } from '@angular/router';
import { CommonModule } from '@angular/common';
import localeEs from '@angular/common/locales/es';
import { AuthService } from '../auth/auth.service';
import { Title } from '@angular/platform-browser';
import { registerLocaleData } from '@angular/common';
import {
  AfterViewChecked,
  Component,
  ElementRef,
  OnInit,
  ViewChild,
  signal,
} from '@angular/core';
import { ProfileService } from '../services/profile.service';
import { ToastService } from '../services/toast.service';
import { STORAGE_KEYS } from '../constants/app-stats';
import { QuantifyModalComponent } from '../cv/quantify-modal.component';
import { CvAuditModalComponent } from '../cv/cv-audit-modal.component';
import { CvImproveModalComponent } from '../cv/cv-improve-modal.component';
import { CvImproveResponse } from '../services/cv-improve.service';
import { RichTextComponent } from '../shared/rich-text/rich-text.component';

@Component({
  selector: 'app-ats-cv',
  imports: [
    CommonModule,
    RouterModule,
    QuantifyModalComponent,
    CvAuditModalComponent,
    CvImproveModalComponent,
    RichTextComponent,
  ],
  standalone: true,
  templateUrl: './ats-cv.component.html',
  styleUrls: ['./ats-cv.component.scss'],
})
export class AtsCvComponent implements OnInit, AfterViewChecked {
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

  /** Offsets en px desde el top del .cv-page donde van los separadores
   * de página visuales. Se recalculan en AfterViewChecked cada vez que
   * cambia la altura del content (re-render por cuantificar, mejorar, etc.). */
  pageBreakOffsets = signal<number[]>([]);
  /** Total de hojas Oficio que ocupa el CV. Mostrado en el header. */
  pageCount = signal<number>(1);

  /**
   * Constantes del formato Oficio (US Legal):
   *   - Page total:  215.9mm × 355.6mm
   *   - Padding usado en .cv-page: 18mm top/bottom, 22mm left/right
   *   - Content height por página: 355.6 - 2*18 = 319.6mm
   *
   * Convertimos a px asumiendo 96 DPI (CSS default): 1mm ≈ 3.7795px.
   * Esto matchea cómo el browser renderea las unidades mm en pantalla.
   *
   * IMPORTANTE: jsPDF slicea la imagen capturada por html2canvas cada
   * 355.6mm desde el TOP ABSOLUTO del .cv-page (incluida la padding).
   * Pero los marcadores visuales son `position: absolute` con `top`
   * relativo al padding-edge (i.e., empieza DESPUÉS del padding-top).
   * Por eso restamos OFICIO_PADDING_TOP_PX al calcular el `top` del
   * marcador — así matchea exactamente dónde jsPDF corta.
   */
  private readonly MM_TO_PX = 3.7795275591;
  private readonly OFICIO_PAGE_HEIGHT_PX = 355.6 * this.MM_TO_PX;
  private readonly OFICIO_PADDING_TOP_PX = 18 * this.MM_TO_PX;

  /** Última altura "natural" medida (sin contar los margin-top
   *  inyectados por snaps). Sirve como cache key: si no cambia, no
   *  re-ejecutamos el snap. Evita loop en ngAfterViewChecked. */
  private lastNaturalHeight = 0;

  /** Modal del auditor — solo se monta cuando se abre (lazy). */
  showAudit = signal(false);

  openAudit(): void {
    this.showAudit.set(true);
  }

  closeAudit(): void {
    this.showAudit.set(false);
  }

  /** Modal del improver — idem auditor, lazy mount. */
  showImprove = signal(false);

  openImprove(): void {
    this.showImprove.set(true);
  }

  closeImprove(): void {
    this.showImprove.set(false);
  }

  /** Recibe la propuesta del modal y la persiste vía PATCH al profile.
   * Optimistic: actualizamos el state local primero para que el user vea
   * el cambio inmediato; si el PATCH falla, rollback + toast. */
  onImproveApplied(proposal: CvImproveResponse): void {
    if (!this.profileData?.id) {
      this.toast.error('No pudimos identificar tu perfil. Recargá la página.');
      return;
    }

    // Snapshot para rollback si el PATCH falla
    const prev = {
      summary: this.profileData.summary,
      professional_title: this.profileData.professional_title,
      skills: this.profileData.skills,
      soft_skills: this.profileData.soft_skills,
      experience: this.profileData.experience,
    };

    // Optimistic update local
    this.profileData = {
      ...this.profileData,
      summary: proposal.summary,
      professional_title: proposal.professional_title,
      skills: proposal.skills,
      soft_skills: proposal.soft_skills,
      experience: proposal.experience,
    };

    // experience al backend va como JSON string (TextField legacy)
    const payload = {
      summary: proposal.summary,
      professional_title: proposal.professional_title,
      skills: proposal.skills,
      soft_skills: proposal.soft_skills,
      experience: JSON.stringify(proposal.experience),
    };

    this.profileService.patchProfile(this.profileData.id, payload).subscribe({
      next: () => {
        this.toast.success('Mejoras aplicadas a tu CV.');
        this.closeImprove();
      },
      error: () => {
        // Rollback
        this.profileData = { ...this.profileData, ...prev };
        this.toast.error('No pudimos guardar las mejoras. Intentá de nuevo.');
        // Modal queda abierto para reintentar
      },
    });
  }

  /** Sample de la primera experiencia para el preview del modal. */
  firstExperienceSample(): { position?: string; description?: string } | null {
    if (!this.isExperienceArray()) return null;
    const first = this.profileData.experience[0];
    return first ? { position: first.position, description: first.description } : null;
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

  /** Después de cada ciclo de detección de cambios, mide la altura real
   * del .cv-page, snappea los page breaks a límites de sección/entry
   * para que no se corten en mitad de un párrafo, y actualiza los
   * markers visuales.
   *
   * Usamos AfterViewChecked en vez de AfterViewInit porque el contenido
   * crece dinámicamente (cuantificar, mejorar, regenerar). El guard
   * `isSnapping` evita re-entry en la misma frame — el snap modifica
   * el DOM y dispara otro view checked. */
  private isSnapping = false;

  ngAfterViewChecked(): void {
    if (!this.cvContent?.nativeElement || this.isExporting()) return;
    if (this.isSnapping) return;
    const el = this.cvContent.nativeElement as HTMLElement;

    // Calcular altura "natural" sin tocar el DOM: scrollHeight actual
    // menos la suma de los margin-top inyectados por snaps previos.
    // Esto es el cache key — si no cambia, no re-snapeamos (evita loop
    // donde ngAfterViewChecked se dispara tras cada DOM mutation y
    // re-ejecuta el snap aunque el contenido sea idéntico).
    const snappedEls = el.querySelectorAll<HTMLElement>('[data-page-snap]');
    let injectedMargin = 0;
    snappedEls.forEach((n) => {
      injectedMargin += parseFloat(n.style.marginTop || '0');
    });
    const naturalHeight = el.scrollHeight - injectedMargin;

    if (Math.abs(naturalHeight - this.lastNaturalHeight) < 4) return;
    this.lastNaturalHeight = naturalHeight;

    this.isSnapping = true;
    try {
      this.resetPageSnaps(el);

      if (naturalHeight <= this.OFICIO_PAGE_HEIGHT_PX + 8) {
        this.pageBreakOffsets.set([]);
        this.pageCount.set(1);
        return;
      }

      this.snapPageBreaks(el);
      this.updateMarkersFromSnaps(el);
    } finally {
      this.isSnapping = false;
    }
  }

  /** Quita los margin-top inyectados por snaps previos para que la
   *  re-medición arranque desde el layout natural. */
  private resetPageSnaps(cvPage: HTMLElement): void {
    cvPage.querySelectorAll<HTMLElement>('[data-page-snap]').forEach((node) => {
      node.style.marginTop = '';
      node.removeAttribute('data-page-snap');
    });
  }

  /** Walks `.cv-entry` (NO .cv-section porque son demasiado grandes —
   *  contienen múltiples entries y empujar la sección entera deja
   *  páginas casi vacías). Para cada entry que cruza el boundary, le
   *  inyecta `margin-top` para que empiece exactamente en el inicio de
   *  la próxima "hoja Oficio".
   *
   *  offsetTop está en coords relativas al padding-edge de .cv-page.
   *  El boundary en esas coords es `N * pageHeight - paddingTop` (porque
   *  jsPDF slicea cada `pageHeight` desde el border-edge y el padding
   *  consume `paddingTop` antes de que empiecen los hijos). */
  private snapPageBreaks(cvPage: HTMLElement): void {
    const pageHeight = this.OFICIO_PAGE_HEIGHT_PX;
    const paddingTop = this.OFICIO_PADDING_TOP_PX;

    const candidates = Array.from(
      cvPage.querySelectorAll<HTMLElement>('.cv-entry'),
    );
    if (candidates.length === 0) return;

    let nextBoundary = pageHeight - paddingTop; // offsetTop coords del primer cut

    for (const el of candidates) {
      // Leer fresh: snaps previos en este loop ya modificaron offsetTop
      // de elementos siguientes.
      const top = el.offsetTop;
      const bottom = top + el.offsetHeight;

      // Si el elemento ya empieza pasada la frontera (porque alguien antes
      // ocupó toda la página), avanzar la frontera hasta cubrirlo.
      while (top >= nextBoundary) {
        nextBoundary += pageHeight;
      }

      // Si cabe entero, sigue. Si lo cruza, snap.
      if (bottom <= nextBoundary) continue;

      const gap = nextBoundary - top;
      if (gap > 6) {
        el.style.marginTop = `${gap}px`;
        el.setAttribute('data-page-snap', '1');
        // Después del snap, su nuevo offsetTop es ~nextBoundary.
        // El boundary siguiente arranca pageHeight más adelante.
        nextBoundary += pageHeight;
      }
    }
  }

  /** Tras el snap, calcula offsets visuales de los markers leyendo la
   *  posición real de los elementos con `data-page-snap`. El marker se
   *  centra en el gap (entre bottom del elemento previo y top del
   *  snappeado). */
  private updateMarkersFromSnaps(cvPage: HTMLElement): void {
    const snapped = cvPage.querySelectorAll<HTMLElement>('[data-page-snap]');
    const offsets: number[] = [];
    const MARKER_HALF_HEIGHT = 27;
    snapped.forEach((el) => {
      const top = el.offsetTop;
      const marginTop = parseFloat(el.style.marginTop || '0');
      // gap visual: top - marginTop hasta top. Centro = top - marginTop/2.
      const gapMid = top - marginTop / 2;
      offsets.push(Math.max(0, gapMid - MARKER_HALF_HEIGHT));
    });
    this.pageBreakOffsets.set(offsets);
    this.pageCount.set(offsets.length + 1);
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
      soft_skills: profile.soft_skills || '',
      languages: this.parseLanguages(profile.languages),
      experience: this.parseExperienceOrEducation(profile.experience),
      education: this.parseExperienceOrEducation(profile.education),
    };
  }

  /** Languages se guardan como JSON-as-text en backend. Acá lo parseamos
   *  a array de `{language, level}`. Tolera: array directo, JSON string,
   *  null/empty. */
  parseLanguages(value: any): { language: string; level: string }[] {
    if (Array.isArray(value)) return value;
    if (typeof value === 'string' && value.trim().startsWith('[')) {
      try {
        const parsed = JSON.parse(value);
        return Array.isArray(parsed) ? parsed : [];
      } catch {
        return [];
      }
    }
    return [];
  }

  /** Splittea la descripción de una experiencia en bullets. El extractor
   *  Gemini formatea cada bullet en una línea con prefijo "• " o "- ".
   *  Si solo hay 1 línea (o 0 bullets), devuelve [] — el template muestra
   *  el texto como un párrafo plano en ese caso. */
  expBullets(description: string | null | undefined): string[] {
    if (!description) return [];
    const lines = description
      .split(/\r?\n/)
      .map((l) => l.trim().replace(/^[•\-*]\s*/, ''))
      .filter(Boolean);
    return lines.length >= 2 ? lines : [];
  }

  /** Skills como array deduplicado para chips/lista del CV. */
  skillsList(): string[] {
    return (this.profileData?.skills || '')
      .split(',')
      .map((s: string) => s.trim())
      .filter(Boolean);
  }

  /** Soft skills idem. Solo se renderea la sección si hay al menos 1. */
  softSkillsList(): string[] {
    return (this.profileData?.soft_skills || '')
      .split(',')
      .map((s: string) => s.trim())
      .filter(Boolean);
  }

  /** True si hay al menos 1 idioma para renderear la sección. */
  hasLanguages(): boolean {
    return Array.isArray(this.profileData?.languages) && this.profileData.languages.length > 0;
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

    // Ocultamos los botones AI + los separadores de página visuales antes
    // de capturar — html2canvas hace screenshot del DOM tal cual, no
    // respeta @media print. La clase `is-exporting` se aplica al wrapper.
    this.isExporting.set(true);

    // Oficio (US Legal) dimensions in points (1 inch = 72 points).
    // Legal = 8.5" × 14" = 612 × 1008 pt.
    const pageWidth = 612;
    const pageHeight = 1008;

    // Damos 1 frame para que el toggle de isExporting() oculte los
    // separadores antes de tomar el screenshot — sin esto, html2canvas
    // captura un frame stale con las líneas de quiebre adentro.
    setTimeout(() => {
      html2canvas(element, {
        scale: 2,
        useCORS: true,
        logging: false,
        backgroundColor: '#ffffff',
      })
        .then((canvas) => {
          const imgData = canvas.toDataURL('image/png');
          const doc = new jsPDF('p', 'pt', 'legal');

          const imgWidth = pageWidth;
          const imgHeight = (canvas.height * pageWidth) / canvas.width;

          // Si el contenido supera la altura de una hoja Oficio, repetimos
          // el render desplazando `position` — la misma imagen rendered
          // se "scrollea" hoja a hoja en el PDF.
          let heightLeft = imgHeight;
          let position = 0;

          doc.addImage(imgData, 'PNG', 0, position, imgWidth, imgHeight);
          heightLeft -= pageHeight;

          while (heightLeft > 0) {
            position = heightLeft - imgHeight;
            doc.addPage();
            doc.addImage(imgData, 'PNG', 0, position, imgWidth, imgHeight);
            heightLeft -= pageHeight;
          }

          doc.save('skiltak-ats-cv.pdf');
          this.isExporting.set(false);
        })
        .catch(() => {
          this.isExporting.set(false);
        });
    }, 50);
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

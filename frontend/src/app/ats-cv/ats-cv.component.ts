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
  computed,
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
import {
  CvProfileData,
  EducationEntry,
  ExperienceEntry,
  LanguageEntry,
  ProfileApiPayload,
  ProfileApiResponse,
} from '../models/profile.model';

/**
 * Tipos de bloque en los que dividimos el CV para la paginación.
 *
 * Reglas de "indivisibilidad":
 *   - header: siempre el primer bloque de la primera hoja.
 *   - summary: párrafo único.
 *   - exp-h2 / edu-h2: solo el heading de sección. Bloque chico,
 *     separado de las entries para que el algoritmo pueda meter más
 *     en la hoja actual. Lookahead evita orphan (h2 nunca al final
 *     de hoja sin entry).
 *   - exp-entry / edu-entry: una entry (puesto + bullets / institución).
 *     No se parte entre hojas; si no cabe, pasa entera a la siguiente.
 *   - exp-text / edu-text: fallback cuando experience/education vienen
 *     como texto libre (no array). Se trata como un único bloque atómico
 *     (incluye su propio h2 adentro).
 *   - skills / soft-skills / languages / portfolio: secciones atómicas
 *     pequeñas — h2 + contenido en un solo bloque.
 */
type BlockKind =
  | 'header'
  | 'summary'
  | 'exp-h2'
  | 'exp-entry'
  | 'exp-text'
  | 'edu-h2'
  | 'edu-entry'
  | 'edu-text'
  | 'skills'
  | 'soft-skills'
  | 'languages'
  | 'portfolio';

interface CvBlock {
  kind: BlockKind;
  /** Para exp-entry / edu-entry: índice en profileData.experience/education. */
  index?: number;
  /** Cuando la entry se parte entre hojas: rango [start, end) de bullets
   *  que se renderean en este block. Sin estos campos = entry completa. */
  bulletStart?: number;
  bulletEnd?: number;
  /** Cuando un exp-text / edu-text se parte entre hojas: rango [start, end)
   *  de líneas del string libre que se renderean en este block. */
  lineStart?: number;
  lineEnd?: number;
  /** True si es la segunda mitad de un bloque partido — el template
   *  pinta un header chiquito "(cont.)" en vez del header completo. */
  isContinuation?: boolean;
}

/** Rango de líneas [start, end) dentro de un text-block parseado. */
type TextEntryRange = { start: number; end: number };

/** Resultado de partir un bloque en dos para distribuirlo entre 2 hojas. */
interface SplitResult {
  part1: CvBlock;
  part1Height: number;
  part2: CvBlock;
  part2Height: number;
}

/**
 * Constantes de paginación. Heurísticas estimadas — no son números
 * exactos, son aproximaciones que funcionan bien en el rango típico de
 * un CV (1-3 hojas). Si cambia mucho el styling de cv-entry/cv-section,
 * recalibrar.
 */
const PAGINATION = {
  /** Hoja Oficio (US Legal) en mm. */
  OFICIO_PAGE_HEIGHT_MM: 355.6,
  /** Padding vertical de la .cv-page (top y bottom). */
  OFICIO_PADDING_MM: 18,
  /** Conversión mm → px asumiendo 96 DPI (CSS default). */
  MM_TO_PX: 3.7795275591,
  /** Altura estimada del cv-entry-header (puesto + empresa + fechas). */
  ENTRY_HEADER_PX: 90,
  /** Overhead estimado del header "(cont.)" en la parte 2 de un split. */
  CONT_HEADER_PX: 35,
  /** Mínimo de bullets en parte 1 para que partir una entry valga la pena. */
  MIN_BULLETS_FIRST_PART: 3,
  /** Altura estimada del h2 "Experiencia profesional" en un text-block. */
  TEXT_SECTION_H2_PX: 50,
  /** Header chiquito "(cont.)" en la parte 2 de un text-block partido. */
  TEXT_CONT_HEADER_PX: 30,
  /** Mínimo de líneas en parte 1 para que partir un text-block valga la pena. */
  MIN_LINES_FIRST_PART: 4,
  /** Mínimo de bullets que tiene que tener un entry para quedarse en parte 1.
   *  Si el último entry de la hoja queda con menos de esto, se mueve entero
   *  a parte 2 (anti-orphan a nivel de entry). Sin este chequeo, vimos casos
   *  donde un entry "Empresa X / Cargo Y" + 1 bullet quedaba huérfano al
   *  pie de página 1 y el resto del entry caía en página 2 — visualmente
   *  feo y rompe el "no cortar entries". */
  MIN_BULLETS_TO_KEEP_ENTRY: 2,
  /** Cap anti-desperdicio del orphan fix: no retroceder el cut si parte 1
   *  queda con menos del N% de lo que cabía. Bajado de 0.5 → 0.4 tras el
   *  caso real del cliente jorgeluisq07 (2026-06-27): el guard abortaba
   *  el orphan fix en CVs largos y el bullet quedaba cortado visualmente
   *  al pie de página. 0.4 da más margen al fix sin vaciar la hoja. */
  MIN_PART1_FILL_RATIO: 0.4,
  /** Factor de seguridad sobre `linesCanFit` en text-block split. La
   *  fórmula `availableForLines / lineAvgHeight` asume que cada línea
   *  ocupa el promedio — pero los bullets largos wrappean a más altura
   *  física que el promedio. Si la última línea calculada es uno de
   *  esos, queda visualmente cortada por overflow:hidden del .cv-page.
   *  Reducir el cap al 85% deja buffer contra esta subestimación. */
  TEXT_SPLIT_SAFETY_RATIO: 0.85,
} as const;

/** Regex de marker de bullet — `-`, `•` o `*` seguido de espacio. */
const BULLET_LINE_RE = /^\s*[-•*]\s+/;

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
  profileData: CvProfileData | null = null;
  isLoading = true;
  errorMessage = '';

  /** Wrapper visible de todas las hojas — usado por html2canvas. */
  @ViewChild('pagesWrap', { static: false }) pagesWrap!: ElementRef<HTMLElement>;
  /** Container off-screen donde medimos altura de cada bloque antes de
   *  decidir en qué hoja entra. */
  @ViewChild('measureRoot', { static: false }) measureRoot!: ElementRef<HTMLElement>;

  /** Cuando está seteado, muestra el modal de cuantificar para esa entry. */
  quantifyTarget = signal<{ index: number; text: string; role: string; company: string } | null>(
    null,
  );
  /** Flag para ocultar los botones AI cuando se captura el PDF. */
  isExporting = signal(false);

  /**
   * Bloques distribuidos en hojas. Cada elemento del array es una hoja
   * (lista de bloques). Lo computa `distributePages()` tras medir.
   */
  pages = signal<CvBlock[][]>([]);
  /** Total de hojas — derivado de pages() con mínimo 1 para que el hint
   *  funcione antes de la primera distribución. */
  pageCount = computed(() => Math.max(1, this.pages().length));

  /** Área útil de contenido por hoja en px. Constante derivada del
   *  formato Oficio menos los paddings vertical superior e inferior. */
  private readonly CONTENT_HEIGHT_PX =
    (PAGINATION.OFICIO_PAGE_HEIGHT_MM - 2 * PAGINATION.OFICIO_PADDING_MM) * PAGINATION.MM_TO_PX;

  /** Cache key del último set de alturas medidas — evita re-distribuir
   *  cuando el DOM no cambió (ngAfterViewChecked dispara seguido). */
  private lastMeasureSignature = '';
  /** Lock para evitar reentrada cuando setear pages() dispara otra detección. */
  private isDistributing = false;

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
    const profile = this.profileData;
    if (!profile?.id) {
      this.toast.error('No pudimos identificar tu perfil. Recarga la página.');
      return;
    }

    const prev = {
      summary: profile.summary,
      professional_title: profile.professional_title,
      skills: profile.skills,
      soft_skills: profile.soft_skills,
      experience: profile.experience,
    };

    this.profileData = {
      ...profile,
      summary: proposal.summary,
      professional_title: proposal.professional_title,
      skills: proposal.skills,
      soft_skills: proposal.soft_skills,
      experience: proposal.experience,
    };

    const payload = {
      summary: proposal.summary,
      professional_title: proposal.professional_title,
      skills: proposal.skills,
      soft_skills: proposal.soft_skills,
      experience: JSON.stringify(proposal.experience),
    };

    this.profileService.patchProfile(profile.id, payload).subscribe({
      next: () => {
        this.toast.success('Mejoras aplicadas a tu CV.');
        this.closeImprove();
      },
      error: () => {
        // Rollback usando el snapshot tomado antes del optimistic update.
        const current = this.profileData;
        if (current) this.profileData = { ...current, ...prev };
        this.toast.error('No pudimos guardar las mejoras. Intenta de nuevo.');
      },
    });
  }

  /** Sample de la primera experiencia para el preview del modal. */
  firstExperienceSample(): { position?: string; description?: string } | null {
    const exps = this.experienceArray();
    if (!exps) return null;
    const first = exps[0];
    return { position: first.position, description: first.description };
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
   * Lista plana de bloques del CV en el orden en que aparecen.
   *
   * Es lo que se renderiza tanto en la measure-layer (para medir alturas)
   * como en la pages-layer (distribuido por hoja).
   *
   * NOTA: esta función se llama en CADA ciclo de change-detection desde
   * el template — debe ser barata. Acá solo armamos un array de tipos
   * + índices, sin trabajo pesado.
   */
  cvBlocks(): CvBlock[] {
    const profile = this.profileData;
    if (!profile) return [];
    const blocks: CvBlock[] = [];
    blocks.push({ kind: 'header' });
    if (profile.summary) blocks.push({ kind: 'summary' });

    const exps = this.experienceArray();
    if (exps) {
      blocks.push({ kind: 'exp-h2' });
      for (let i = 0; i < exps.length; i++) {
        blocks.push({ kind: 'exp-entry', index: i });
      }
    } else if (profile.experience) {
      blocks.push({ kind: 'exp-text' });
    }

    const edus = this.educationArray();
    if (edus) {
      blocks.push({ kind: 'edu-h2' });
      for (let i = 0; i < edus.length; i++) {
        blocks.push({ kind: 'edu-entry', index: i });
      }
    } else if (profile.education) {
      blocks.push({ kind: 'edu-text' });
    }

    if (profile.skills) blocks.push({ kind: 'skills' });
    if (this.softSkillsList().length > 0) blocks.push({ kind: 'soft-skills' });
    if (this.hasLanguages()) blocks.push({ kind: 'languages' });
    if (profile.portfolio_url) blocks.push({ kind: 'portfolio' });

    return blocks;
  }

  /** Devuelve el array de experiencias si el profile las tiene como
   *  estructuradas (no texto libre), sino null. Centraliza el guard
   *  Array.isArray + length > 0 que de otro modo se repetiría en cada
   *  caller. */
  experienceArray(): ExperienceEntry[] | null {
    const exp = this.profileData?.experience;
    return Array.isArray(exp) && exp.length > 0 ? exp : null;
  }

  /** Idem para educación. */
  educationArray(): EducationEntry[] | null {
    const edu = this.profileData?.education;
    return Array.isArray(edu) && edu.length > 0 ? edu : null;
  }

  /** Lookup tipado de una experiencia por índice — para usar en templates
   *  con `*ngIf="expAt(i) as exp"` que evita las cadenas
   *  `experienceArray()?.[i]?.field` repetidas. */
  expAt(index: number | undefined): ExperienceEntry | null {
    if (index === undefined) return null;
    return this.experienceArray()?.[index] ?? null;
  }

  /** Idem para una entry de educación. */
  eduAt(index: number | undefined): EducationEntry | null {
    if (index === undefined) return null;
    return this.educationArray()?.[index] ?? null;
  }

  /** Devuelve experience como string (fallback markdown) o '' si está
   *  estructurada como array. Usado por el template expTextTpl que solo
   *  se invoca para bloques exp-text. */
  expText(): string {
    const v = this.profileData?.experience;
    return typeof v === 'string' ? v : '';
  }

  /** Idem para education. */
  eduText(): string {
    const v = this.profileData?.education;
    return typeof v === 'string' ? v : '';
  }

  /**
   * Tras cada ciclo de detección de cambios, medimos alturas de los
   * bloques en la measure-layer y los distribuimos en hojas. La cache
   * (`lastMeasureSignature`) evita re-distribuir cuando el DOM no
   * cambió — sin eso entraríamos en loop infinito porque setear
   * pages() dispara otro ngAfterViewChecked.
   */
  ngAfterViewChecked(): void {
    if (this.isExporting() || this.isDistributing) return;
    this.distributePages();
  }

  /**
   * Distribución greedy: para cada bloque en orden, lo agregamos a la
   * hoja actual; si no entra (excede la altura útil), abrimos una hoja
   * nueva y lo ponemos ahí. Si un bloque por sí solo es más alto que
   * la hoja, se acepta el overflow (no podemos cortarlo — el contrato
   * con el user es "bloques indivisibles"). Visualmente, el overflow:
   * hidden del .cv-page lo recorta y el user nota que tiene que reducir
   * ese bloque.
   */
  private distributePages(): void {
    const root = this.measureRoot?.nativeElement;
    if (!root) return;

    const measured = root.querySelectorAll<HTMLElement>('[data-measure-block]');
    if (measured.length === 0) {
      // Sin bloques: aún no cargó profileData. No reseteamos pages() para
      // evitar parpadeo si justo recibimos data parcial.
      return;
    }

    // Heights: incluimos margen-top + margen-bottom porque cv-section
    // tiene margin-bottom 6mm que necesitamos contar para el spacing.
    // Nota: .cv-measure-block tiene overflow:hidden para que los margenes
    // de su hijo NO se collapsen con el contenedor — así offsetHeight
    // incluye los márgenes interiores del cv-section.
    const heights: number[] = [];
    measured.forEach((b) => {
      const cs = getComputedStyle(b);
      const mt = parseFloat(cs.marginTop || '0');
      const mb = parseFloat(cs.marginBottom || '0');
      heights.push(b.offsetHeight + mt + mb);
    });

    const signature = `${measured.length}|${heights.map((h) => h.toFixed(1)).join(',')}`;
    if (signature === this.lastMeasureSignature) return;
    this.lastMeasureSignature = signature;

    this.isDistributing = true;
    try {
      const originalBlocks = this.cvBlocks();
      const limit = this.CONTENT_HEIGHT_PX;
      const result: CvBlock[][] = [[]];
      let currentHeight = 0;

      // Cola mutable {block, height} — necesaria porque los splits de
      // entries insertan bloques nuevos a mitad de la iteración.
      const queue: Array<{ block: CvBlock; height: number }> = originalBlocks.map((b, i) => ({
        block: b,
        height: heights[i] ?? 0,
      }));

      let i = 0;
      while (i < queue.length) {
        const { block, height: h } = queue[i];
        const currentPage = result[result.length - 1];

        // Anti-orphan SUAVE: si es un h2 de sección, considerá pushear
        // a hoja nueva — PERO antes verificá si la entry siguiente se
        // puede partir entre bullets y llenar mejor la hoja actual.
        // Si el split es viable, NO antiorphan — dejá h2 acá; la entry
        // se va a partir cuando se procese.
        const isH2 = block.kind === 'exp-h2' || block.kind === 'edu-h2';
        const nextBlock = queue[i + 1]?.block;
        const nextIsFirstEntry =
          (block.kind === 'exp-h2' && nextBlock?.kind === 'exp-entry' && nextBlock.index === 0) ||
          (block.kind === 'edu-h2' && nextBlock?.kind === 'edu-entry' && nextBlock.index === 0);
        if (isH2 && nextIsFirstEntry && currentPage.length > 0) {
          const nextH = queue[i + 1].height;
          const combined = h + nextH;
          if (currentHeight + combined > limit) {
            // Combined no entra. ¿Vale la pena anti-orphan?
            //   - SI: combined cabe en una hoja fresh Y la entry no puede
            //     partirse de forma útil → push h2 a hoja nueva.
            //   - NO: la entry tiene bullets que se pueden partir y llenar
            //     esta hoja → dejá h2 acá, el split del entry hace el resto.
            const availableAfterH2 = limit - currentHeight - h;
            const canSplit = this.canMeaningfullySplit(queue[i + 1].block, nextH, availableAfterH2);
            if (!canSplit && combined <= limit) {
              // Antiorphan tradicional: combined fits fresh, entry no se parte
              result.push([block]);
              currentHeight = h;
              i++;
              continue;
            }
            // Else: fall through — h2 se queda; la próxima iter procesa
            // la entry y dispara split si corresponde.
          }
        }

        // Salvaguarda: hoja con SOLO un h2 fresh → forzá la entry acá.
        const onlyHasH2 =
          currentPage.length === 1 &&
          (currentPage[0].kind === 'exp-h2' || currentPage[0].kind === 'edu-h2');
        if (onlyHasH2) {
          currentPage.push(block);
          currentHeight += h;
          i++;
          continue;
        }

        // Standard greedy
        if (currentPage.length > 0 && currentHeight + h > limit) {
          // No entra. Intentos de split en orden:
          //   1) Entry estructurada (array de objetos) → split por bullets.
          //   2) Text libre (experience/education como string markdown) →
          //      split por líneas del string.
          const entrySplit = this.maybeSplitEntry(block, h, limit - currentHeight);
          if (entrySplit) {
            currentPage.push(entrySplit.part1);
            currentHeight += entrySplit.part1Height;
            queue.splice(i + 1, 0, { block: entrySplit.part2, height: entrySplit.part2Height });
            i++;
            continue;
          }

          const textSplit = this.maybeSplitText(block, h, limit - currentHeight);
          if (textSplit) {
            currentPage.push(textSplit.part1);
            currentHeight += textSplit.part1Height;
            queue.splice(i + 1, 0, { block: textSplit.part2, height: textSplit.part2Height });
            i++;
            continue;
          }

          // No se pudo partir → hoja nueva
          result.push([block]);
          currentHeight = h;
        } else {
          // Entra → push
          currentPage.push(block);
          currentHeight += h;
        }
        i++;
      }

      this.pages.set(result);
    } finally {
      // Liberamos el lock en el siguiente tick — sino el set anterior
      // dispara ngAfterViewChecked re-entrante en este mismo callstack.
      queueMicrotask(() => (this.isDistributing = false));
    }
  }

  /**
   * Carga el perfil. Si el user está autenticado SIEMPRE pedimos al
   * backend — necesitamos el `id` para que features como "Mejorar con
   * AI" o "Cuantificar" puedan hacer PATCH al profile correcto. Antes
   * leíamos `MANUAL_PROFILE_DRAFT` de localStorage primero, pero el
   * draft del wizard NO incluye id → al confirmar una mejora fallaba
   * con "No pudimos identificar tu perfil".
   *
   * El draft sigue siendo el fallback SOLO cuando no hay sesión activa
   * (e.g., preview mid-wizard antes de registrarse).
   */
  loadProfileData(): void {
    if (this.authService.isAuthenticated()) {
      this.fetchProfileFromBackend();
      return;
    }
    const savedData = localStorage.getItem(STORAGE_KEYS.MANUAL_PROFILE_DRAFT);
    if (savedData) {
      try {
        const draft = JSON.parse(savedData) as CvProfileData;
        if (!draft.email) {
          const userEmail = sessionStorage.getItem('user_email');
          if (userEmail) draft.email = userEmail;
        }
        this.profileData = draft;
        this.isLoading = false;
        return;
      } catch (e) {
        console.error('Error parsing localStorage data:', e);
      }
    }
    this.errorMessage = 'No se encontraron datos del perfil';
    this.isLoading = false;
  }

  fetchProfileFromBackend(): void {
    if (!this.authService.isAuthenticated()) {
      this.errorMessage = 'No se encontraron datos del perfil';
      this.isLoading = false;
      return;
    }

    this.profileService.getMyProfile().subscribe({
      next: (response: ProfileApiPayload) => {
        const raw = this.unwrapProfileResponse(response);
        if (raw) {
          this.profileData = this.formatProfileData(raw);
        } else {
          this.errorMessage = 'No se encontraron datos del perfil';
        }
        this.isLoading = false;
      },
      error: (err: unknown) => {
        console.error('Error loading profile:', err);
        this.errorMessage = 'Error al cargar el perfil';
        this.isLoading = false;
      },
    });
  }

  /** El endpoint puede devolver paginated `{results}`, array crudo o
   *  objeto singular. Acá unificamos a "primer profile o null". */
  private unwrapProfileResponse(payload: ProfileApiPayload): ProfileApiResponse | null {
    if (!payload) return null;
    if (Array.isArray(payload)) return payload[0] ?? null;
    if ('results' in payload && Array.isArray(payload.results)) {
      return payload.results[0] ?? null;
    }
    return payload as ProfileApiResponse;
  }

  /** Normaliza la respuesta cruda del backend al shape `CvProfileData`
   *  que consumen templates y algoritmo de paginación. Aplica defaults
   *  a strings vacíos y parsea los TextField legacy (JSON-as-string)
   *  para experience/education/languages. */
  formatProfileData(profile: ProfileApiResponse): CvProfileData {
    return {
      id: profile.id ?? null,
      first_name: profile.first_name ?? '',
      last_name: profile.last_name ?? '',
      email: profile.user?.email ?? profile.email ?? '',
      number_id: profile.number_id ?? '',
      phone_code: profile.phone_code ?? '',
      phone_number: profile.phone_number ?? profile.phone ?? '',
      city: profile.city ?? '',
      country: profile.country ?? '',
      professional_title: profile.professional_title ?? '',
      summary: profile.summary ?? '',
      linkedin_url: profile.linkedin_url ?? '',
      portfolio_url: profile.portfolio_url ?? '',
      skills: profile.skills ?? '',
      soft_skills: profile.soft_skills ?? '',
      languages: this.parseLanguages(profile.languages),
      experience: this.parseEntriesField<ExperienceEntry>(profile.experience),
      education: this.parseEntriesField<EducationEntry>(profile.education),
    };
  }

  /** Languages se guarda como JSON-as-string en backend. Devolvemos
   *  array vacío para los casos null/string-inválido en vez de propagar
   *  el TypeError al template. */
  parseLanguages(value: LanguageEntry[] | string | null | undefined): LanguageEntry[] {
    if (Array.isArray(value)) return value;
    if (typeof value === 'string' && value.trim().startsWith('[')) {
      try {
        const parsed: unknown = JSON.parse(value);
        return Array.isArray(parsed) ? (parsed as LanguageEntry[]) : [];
      } catch {
        return [];
      }
    }
    return [];
  }

  /**
   * Splittea la descripción de una experiencia en bullets canónicos
   * (sin marker `-`/`•`/`*` y sin espacios extra). Solo devuelve bullets
   * si hay ≥ 2 líneas significativas — sino tratamos la descripción como
   * un párrafo libre que NO se parte.
   */
  expBullets(description: string | null | undefined): string[] {
    if (!description) return [];
    const lines = description
      .split(/\r?\n/)
      .map((l) => l.trim().replace(/^[•\-*]\s*/, ''))
      .filter(Boolean);
    return lines.length >= 2 ? lines : [];
  }

  softSkillsList(): string[] {
    return (this.profileData?.soft_skills ?? '')
      .split(',')
      .map((s) => s.trim())
      .filter(Boolean);
  }

  hasLanguages(): boolean {
    return (this.profileData?.languages?.length ?? 0) > 0;
  }

  /**
   * Normaliza `experience` / `education` (campos polimórficos del
   * backend) a `T[]` cuando vienen como array o como JSON-string
   * serializado, sino mantiene el string libre para el fallback de
   * markdown plano. El genérico evita duplicar la función para cada
   * shape de entry.
   */
  parseEntriesField<T>(value: T[] | string | null | undefined): T[] | string {
    if (Array.isArray(value)) return value;
    if (!value) return '';
    const trimmed = value.trim();
    if (trimmed.startsWith('[') || trimmed.startsWith('{')) {
      try {
        const parsed: unknown = JSON.parse(trimmed);
        if (Array.isArray(parsed)) return parsed as T[];
      } catch {
        /* fall through */
      }
    }
    return value;
  }

  // ---- Cuantificar logros con AI -----------------------------------

  openQuantify(index: number): void {
    const exps = this.experienceArray();
    const exp = exps?.[index];
    if (!exp?.description) return;
    this.quantifyTarget.set({
      index,
      text: exp.description,
      role: exp.position ?? '',
      company: exp.company ?? '',
    });
  }

  closeQuantify(): void {
    this.quantifyTarget.set(null);
  }

  onQuantifyApplied(newText: string): void {
    const target = this.quantifyTarget();
    if (!target) return;
    const profile = this.profileData;
    const exps = this.experienceArray();
    if (!profile?.id || !exps) {
      this.toast.error('No pudimos identificar tu perfil. Recarga la página.');
      return;
    }

    const previousText = exps[target.index].description;
    exps[target.index] = { ...exps[target.index], description: newText };
    this.closeQuantify();

    const payload = { experience: JSON.stringify(exps) };
    this.profileService.patchProfile(profile.id, payload).subscribe({
      next: () => {
        this.toast.success('Logro actualizado en tu CV.');
      },
      error: () => {
        exps[target.index] = { ...exps[target.index], description: previousText };
        this.toast.error('No pudimos guardar el cambio. Intenta de nuevo.');
      },
    });
  }

  /**
   * Exporta las hojas a PDF. Captura cada `.cv-page` por separado y la
   * agrega como una página independiente del PDF — así cada hoja del
   * documento exportado tiene su propio padding top/bottom (no hay
   * artefactos de "una hoja larga sliceada").
   *
   * `isExporting` oculta los botones AI antes de capturar (html2canvas
   * no respeta @media print, hay que toggle de clase manual).
   */
  async downloadCV(): Promise<void> {
    if (!this.pagesWrap?.nativeElement) return;
    const pageEls = Array.from(
      this.pagesWrap.nativeElement.querySelectorAll<HTMLElement>('.cv-page'),
    );
    if (pageEls.length === 0) return;

    this.isExporting.set(true);
    // Damos un frame para que la clase is-exporting oculte los botones.
    await new Promise((resolve) => setTimeout(resolve, 50));

    // Legal/Oficio en puntos (1 inch = 72 pt): 8.5" × 14" = 612 × 1008 pt.
    const pageWidth = 612;
    try {
      const doc = new jsPDF('p', 'pt', 'legal');
      for (let i = 0; i < pageEls.length; i++) {
        const canvas = await html2canvas(pageEls[i], {
          scale: 2,
          useCORS: true,
          logging: false,
          backgroundColor: '#ffffff',
        });
        const imgData = canvas.toDataURL('image/png');
        // Mantenemos proporción ancho-alto del canvas dentro del ancho
        // fijo del PDF. Si la hoja DOM es exactamente Oficio, imgHeight
        // sale ~1008pt y llena la página completa.
        const imgHeight = (canvas.height * pageWidth) / canvas.width;
        if (i > 0) doc.addPage();
        doc.addImage(imgData, 'PNG', 0, 0, pageWidth, imgHeight);
      }
      doc.save('skiltak-ats-cv.pdf');
    } catch (err) {
      console.error('PDF export failed:', err);
      this.toast.error('No pudimos exportar el PDF. Intenta de nuevo.');
    } finally {
      this.isExporting.set(false);
    }
  }

  goToDashboard() {
    if (!this.authService.isAuthenticated()) {
      sessionStorage.setItem('redirect_after_login', '/dashboard');
      this.router.navigate(['/auth/login']);
    } else {
      this.router.navigate(['/dashboard']);
    }
  }

  isEducationArray(): boolean {
    return this.educationArray() !== null;
  }

  isExperienceArray(): boolean {
    return this.experienceArray() !== null;
  }

  /** trackBy del *ngFor de páginas — basa en índice + cantidad de bloques
   *  para no remontar todas las hojas cuando cambia solo una. */
  trackPage(index: number, page: CvBlock[]): string {
    return `${index}-${page.length}`;
  }

  /** Predicado: ¿la entry tiene bullets como para partirse de forma útil
   *  en `availableHeight`? Usado por el anti-orphan para decidir si hay
   *  alternativa mejor antes de pushear el h2 a hoja nueva. */
  private canMeaningfullySplit(
    block: CvBlock,
    fullHeight: number,
    availableHeight: number,
  ): boolean {
    const bullets = this.entryBulletsFor(block);
    if (bullets === null || bullets.length < 2) return false;
    const bulletAvg = (fullHeight - PAGINATION.ENTRY_HEADER_PX) / bullets.length;
    if (bulletAvg <= 0) return false;
    const bulletsCanFit = Math.max(
      0,
      Math.floor((availableHeight - PAGINATION.ENTRY_HEADER_PX) / bulletAvg),
    );
    return bulletsCanFit >= PAGINATION.MIN_BULLETS_FIRST_PART && bulletsCanFit < bullets.length;
  }

  /**
   * Si el bloque es una entry de experiencia/educación con bullets y
   * no cabe en `availableHeight`, intenta partirla: parte 1 (header +
   * primeros N bullets) en la hoja actual, parte 2 (cont. header +
   * resto de bullets) en la siguiente. Devuelve null si la entry no
   * tiene suficientes bullets para que el split valga la pena.
   *
   * Estimación de heights: dividimos (h - headerPx) entre la cantidad
   * de bullets para sacar un avg por bullet, y calculamos cuántos
   * entran. No es perfectamente preciso (algunos bullets son más largos
   * que otros) pero es buena heurística para evitar desperdiciar hoja.
   */
  private maybeSplitEntry(
    block: CvBlock,
    fullHeight: number,
    availableHeight: number,
  ): SplitResult | null {
    const bullets = this.entryBulletsFor(block);
    if (bullets === null || bullets.length < 2) return null;

    const totalBullets = bullets.length;
    const bulletsTotalHeight = Math.max(fullHeight - PAGINATION.ENTRY_HEADER_PX, 0);
    const bulletAvgHeight = bulletsTotalHeight / totalBullets;
    if (bulletAvgHeight <= 0) return null;

    const availableForBullets = availableHeight - PAGINATION.ENTRY_HEADER_PX;
    const bulletsCanFit = Math.max(0, Math.floor(availableForBullets / bulletAvgHeight));
    if (bulletsCanFit < PAGINATION.MIN_BULLETS_FIRST_PART) return null;
    if (bulletsCanFit >= totalBullets) return null;

    const part1: CvBlock = {
      kind: block.kind,
      index: block.index,
      bulletEnd: bulletsCanFit,
    };
    const part2: CvBlock = {
      kind: block.kind,
      index: block.index,
      bulletStart: bulletsCanFit,
      isContinuation: true,
    };
    const part1Height = PAGINATION.ENTRY_HEADER_PX + bulletsCanFit * bulletAvgHeight;
    const part2Height =
      PAGINATION.CONT_HEADER_PX + (totalBullets - bulletsCanFit) * bulletAvgHeight;
    return { part1, part1Height, part2, part2Height };
  }

  /**
   * Lookup de bullets para una entry partible. Centraliza los guards
   * (kind correcto, no es continuation, no es ya-partido, entry existe
   * en profileData) para evitar duplicarlos en maybeSplitEntry y
   * canMeaningfullySplit. Devuelve null si el bloque no es candidato.
   */
  private entryBulletsFor(block: CvBlock): string[] | null {
    if (block.kind !== 'exp-entry' && block.kind !== 'edu-entry') return null;
    if (block.bulletStart !== undefined || block.bulletEnd !== undefined) return null;
    if (block.isContinuation) return null;
    if (block.index === undefined) return null;

    const arr = block.kind === 'exp-entry' ? this.experienceArray() : this.educationArray();
    const entry = arr?.[block.index];
    if (!entry || !('description' in entry) || !entry.description) return null;
    return this.expBullets(entry.description);
  }

  /**
   * Split de bloques `exp-text` / `edu-text` (caso legacy donde el campo
   * viene como string markdown libre, no como array de objetos).
   *
   * Estrategia en 3 pasos, de más limpia a más invasiva:
   *
   *   1. PARSE: dividir el string en "entries lógicas" — un entry =
   *      grupo de líneas consecutivas que arranca con uno o más headers
   *      (líneas bold o no-bullet) y sigue con sus bullets, hasta que
   *      aparece el header del próximo entry o se acaba el texto.
   *
   *   2. ENTRY-LEVEL SPLIT: greedy fit de entries enteras. Cortar EN EL
   *      BORDE entre entries (corte limpio: hoja 2 arranca con un entry
   *      fresh). Esto es lo que pide cualquier CV bien formateado.
   *
   *   3. FALLBACK LINE-LEVEL SPLIT: si NI el primer entry cabe en lo
   *      que queda de hoja, recurrimos al split línea-por-línea con
   *      anti-orphan backtrack (un solo entry monolítico que se reparte
   *      entre 2 hojas). Caso raro pero hay que cubrirlo.
   */
  private maybeSplitText(
    block: CvBlock,
    fullHeight: number,
    availableHeight: number,
  ): SplitResult | null {
    if (block.kind !== 'exp-text' && block.kind !== 'edu-text') return null;
    if (block.lineStart !== undefined || block.lineEnd !== undefined) return null;
    if (block.isContinuation) return null;

    const raw = this.rawTextFor(block.kind);
    if (!raw) return null;

    const lines = raw.split(/\r?\n/);
    if (lines.length < PAGINATION.MIN_LINES_FIRST_PART) return null;

    const linesTotalHeight = Math.max(fullHeight - PAGINATION.TEXT_SECTION_H2_PX, 0);
    const lineAvgHeight = linesTotalHeight / lines.length;
    if (lineAvgHeight <= 0) return null;
    const availableForLines = availableHeight - PAGINATION.TEXT_SECTION_H2_PX;
    if (availableForLines <= 0) return null;
    // Safety margin: la fórmula promedio subestima cuando hay bullets
    // largos que wrappean. Reducir el cap evita que la última línea
    // calculada quede visualmente cortada por overflow:hidden del
    // .cv-page. Sin esto, vimos en producción casos donde el algoritmo
    // estimaba 4 líneas pero solo entraban 3 + medio bullet.
    const linesCanFit = Math.floor(
      (availableForLines / lineAvgHeight) * PAGINATION.TEXT_SPLIT_SAFETY_RATIO,
    );
    if (linesCanFit < PAGINATION.MIN_LINES_FIRST_PART) return null;
    if (linesCanFit >= lines.length) return null;

    // Paso 1: parsear el texto en entries lógicas.
    const entries = this.parseTextEntries(lines);

    // Paso 2: con múltiples entries, preferimos cortar EN EL BORDE entre
    // entries (corte limpio: hoja 2 arranca con un entry fresh).
    if (entries.length >= 2) {
      const entrySplit = this.cutAtEntryBoundary(entries, linesCanFit);
      if (entrySplit !== null && entrySplit >= PAGINATION.MIN_LINES_FIRST_PART) {
        const refined = this.avoidEntryOrphan(lines, entrySplit, linesCanFit);
        return this.buildTextSplit(block, lines, refined, lineAvgHeight);
      }
    }

    // Paso 3: fallback line-level con anti-orphan backtrack — si el cut
    // cae sobre un header (no-bullet), lo retrocedemos hasta que la
    // última línea de parte 1 sea un bullet.
    const lineLevelCut = this.backtrackToBullet(lines, linesCanFit);
    if (lineLevelCut < PAGINATION.MIN_LINES_FIRST_PART) return null;
    if (lineLevelCut >= lines.length) return null;

    // Paso 4: anti-orphan a nivel de entry. Si el último header line en
    // parte 1 quedó con muy pocos bullets (header + 0-1 bullets), retrocedé
    // el cut para mover ese entry entero a parte 2. Capeado por
    // MIN_PART1_FILL_RATIO para no vaciar la hoja.
    const finalCut = this.avoidEntryOrphan(lines, lineLevelCut, linesCanFit);
    return this.buildTextSplit(block, lines, finalCut, lineAvgHeight);
  }

  /**
   * Anti-orphan a nivel de entry: si parte 1 termina con un header
   * (puesto/empresa) seguido de muy pocos bullets, movemos ese header
   * entero a parte 2 para que viaje con el resto de sus bullets.
   *
   * Diferencia con `backtrackToBullet`: ese solo evita que el cut caiga
   * EXACTAMENTE sobre un header (huérfano de 0 bullets). Este chequea
   * el conteo de bullets después del último header en parte 1 y
   * retrocede si está debajo del threshold.
   *
   * Guardrail: si el retroceso deja parte 1 con menos del fill ratio
   * mínimo, abortar — preferimos un orphan visual a una hoja casi vacía.
   * Caso típico de aborto: el entry "huérfano" es ENORME (10 bullets)
   * y moverlo a parte 2 vaciaría la mitad de la hoja.
   */
  private avoidEntryOrphan(lines: string[], cut: number, linesCanFit: number): number {
    if (cut <= 0) return cut;

    // Contar bullets consecutivos antes del cut (saltando blanks finales
    // que `backtrackToBullet` debería haber comido, defensivo).
    let i = cut - 1;
    while (i >= 0 && this.isBlankLine(lines[i])) i--;
    let bulletsAfterHeader = 0;
    while (i >= 0 && this.isBulletLine(lines[i])) {
      bulletsAfterHeader++;
      i--;
    }
    // Si todo eran bullets hasta el inicio del texto: no hay header
    // huérfano que mover.
    if (i < 0) return cut;
    // Suficientes bullets después del último header → no es orphan.
    if (bulletsAfterHeader >= PAGINATION.MIN_BULLETS_TO_KEEP_ENTRY) return cut;

    // Retroceder al INICIO del bloque de header lines (puede ser
    // "Empresa\nCargo [fechas]" = 2 headers seguidos sin bullets entre
    // medio — los englobamos todos).
    let headerStart = i;
    while (headerStart > 0 && this.isHeaderLine(lines[headerStart - 1])) {
      headerStart--;
    }
    // Saltar blanks anteriores al header para que parte 1 termine en
    // bullet o en EOF lógico, no en blanco.
    let newCut = headerStart;
    while (newCut > 0 && this.isBlankLine(lines[newCut - 1])) newCut--;

    // Guard anti-desperdicio: si retroceder vacía demasiado la hoja,
    // mejor dejar el orphan visual.
    const minAcceptable = Math.max(
      PAGINATION.MIN_LINES_FIRST_PART,
      Math.floor(linesCanFit * PAGINATION.MIN_PART1_FILL_RATIO),
    );
    if (newCut < minAcceptable) return cut;
    return newCut;
  }

  /** Devuelve el string crudo (legacy) de experience/education según el
   *  kind del bloque, o null si no está como texto libre. */
  private rawTextFor(kind: 'exp-text' | 'edu-text'): string | null {
    const value = kind === 'exp-text' ? this.profileData?.experience : this.profileData?.education;
    return typeof value === 'string' && value.trim() ? value : null;
  }

  // ---- Predicados de clasificación de líneas ------------------------
  // Usados tanto por parseTextEntries como por backtrackToBullet. Tener
  // una sola definición evita drift si más adelante agregamos markers
  // (por ej. `+ ` o `~`) o cambia el formato.

  private isBulletLine(line: string): boolean {
    return BULLET_LINE_RE.test(line);
  }
  private isBlankLine(line: string): boolean {
    return !line.trim();
  }
  private isHeaderLine(line: string): boolean {
    return !this.isBlankLine(line) && !this.isBulletLine(line);
  }

  /**
   * Parsea un array de líneas (texto markdown libre) en entries lógicas.
   * Un entry = una o más líneas de header (bold / no-bullet / no-blank)
   * seguidas de sus líneas de contenido (bullets, párrafos, blanks),
   * hasta que aparece el próximo header (transición bullet/blank → header).
   *
   * Si el texto NO tiene headers (solo bullets sueltos), devuelve un
   * único entry con todo el contenido — el caller cae al fallback
   * line-level.
   */
  private parseTextEntries(lines: string[]): TextEntryRange[] {
    const entries: TextEntryRange[] = [];
    let i = 0;
    // Saltar blanks iniciales.
    while (i < lines.length && this.isBlankLine(lines[i])) i++;
    if (i >= lines.length) return entries;

    let entryStart = i;
    while (i < lines.length) {
      // Inicio de nuevo entry: header después de bullet/blank
      // (transición no-header → header).
      const prev = i > entryStart ? lines[i - 1] : '';
      const curr = lines[i];
      const isNewEntryBoundary =
        i > entryStart &&
        this.isHeaderLine(curr) &&
        (this.isBulletLine(prev) || this.isBlankLine(prev));
      if (isNewEntryBoundary) {
        // Cerrar entry anterior recortando blanks finales.
        let end = i;
        while (end > entryStart && this.isBlankLine(lines[end - 1])) end--;
        entries.push({ start: entryStart, end });
        entryStart = i;
      }
      i++;
    }
    // Cerrar el último entry.
    let end = lines.length;
    while (end > entryStart && this.isBlankLine(lines[end - 1])) end--;
    if (end > entryStart) entries.push({ start: entryStart, end });
    return entries;
  }

  /**
   * Dado un set de entries y el máximo de líneas que entran en parte 1,
   * devuelve el índice de línea donde cortar (= primer line del primer
   * entry que no entra). Si NI el primer entry entra → null (caller
   * debe fallback a line-level).
   */
  private cutAtEntryBoundary(entries: TextEntryRange[], linesCanFit: number): number | null {
    let cumulative = 0;
    let lastEntryEndThatFit = 0;
    for (const e of entries) {
      const entryLines = e.end - e.start;
      if (cumulative + entryLines > linesCanFit) {
        return lastEntryEndThatFit > 0 ? lastEntryEndThatFit : null;
      }
      cumulative += entryLines;
      lastEntryEndThatFit = e.end;
    }
    return null;
  }

  /**
   * Anti-orphan para line-level fallback: retrocede el cut mientras la
   * última línea de parte 1 NO sea un bullet — moviendo headers o blanks
   * a parte 2 para que viajen junto a sus bullets.
   */
  private backtrackToBullet(lines: string[], initialCut: number): number {
    let cut = initialCut;
    while (cut > 0 && !this.isBulletLine(lines[cut - 1] ?? '')) {
      cut--;
    }
    return cut;
  }

  /** Construye el par {part1, part2} de un text-block partido. Heights
   *  se estiman usando la altura promedio por línea + overheads del h2
   *  y del header "(cont.)". */
  private buildTextSplit(
    block: CvBlock,
    lines: string[],
    cut: number,
    lineAvgHeight: number,
  ): SplitResult {
    const part1: CvBlock = { kind: block.kind, lineEnd: cut };
    const part2: CvBlock = { kind: block.kind, lineStart: cut, isContinuation: true };
    const part1Height = PAGINATION.TEXT_SECTION_H2_PX + cut * lineAvgHeight;
    const part2Height = PAGINATION.TEXT_CONT_HEADER_PX + (lines.length - cut) * lineAvgHeight;
    return { part1, part1Height, part2, part2Height };
  }

  /** Devuelve el slice de líneas de un text-block (experience/education
   *  como string libre) — usado por los templates expTextTpl/eduTextTpl
   *  cuando el bloque renderea solo una parte tras un split. */
  getTextBlockSlice(kind: 'exp' | 'edu', start?: number, end?: number): string {
    const raw = kind === 'exp' ? this.profileData?.experience : this.profileData?.education;
    if (typeof raw !== 'string') return '';
    if (start === undefined && end === undefined) return raw;
    return raw
      .split(/\r?\n/)
      .slice(start ?? 0, end)
      .join('\n');
  }

  /**
   * Devuelve el slice de bullets de una entry como markdown — usado por
   * el template cuando el bloque renderea solo una parte (split).
   *
   * NOTA: re-emitimos los bullets siempre con `- ` como marker canónico.
   * Si el original venía con `•` o `*`, se normaliza. RichTextComponent
   * los renderea idénticos, así que el output visual no cambia.
   */
  getEntryBulletsMarkdown(
    entryIdx: number,
    kind: 'exp' | 'edu',
    start?: number,
    end?: number,
  ): string {
    const arr = kind === 'exp' ? this.experienceArray() : this.educationArray();
    const entry = arr?.[entryIdx];
    // EducationEntry no tiene description — el split solo aplica a exp.
    if (!entry || !('description' in entry) || !entry.description) return '';
    if (start === undefined && end === undefined) return entry.description;
    const bullets = this.expBullets(entry.description);
    return bullets
      .slice(start ?? 0, end)
      .map((b) => `- ${b}`)
      .join('\n');
  }
}

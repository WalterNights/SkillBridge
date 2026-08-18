import { Country } from 'country-state-city';
import { CommonModule } from '@angular/common';
import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { DomSanitizer, SafeHtml, Title } from '@angular/platform-browser';
import { FormArray, FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router, RouterModule } from '@angular/router';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { ProfileBuilderComponent } from '../../shared/profile-builder/profile-builder.component';
import { CountryCode } from '../../models/country-code.model';
import { CountryCodeService } from '../../services/country-code.service';
import { ProfileService } from '../../services/profile.service';
import { AuthService } from '../../auth/auth.service';
import { environment } from '../../../environment/environment';
import { STORAGE_KEYS } from '../../constants/app-stats';
import { PhotoCropperDialogComponent } from '../../shared/photo-cropper/photo-cropper-dialog.component';
import { TextFormatToolbarComponent } from '../../shared/text-format-toolbar/text-format-toolbar.component';
import {
  CvFontSize,
  CvLanguage,
  CvTextAlign,
  EducationEntry,
  ExperienceEntry,
  LanguageEntry,
} from '../../models/profile.model';
import {
  parseLegacyEducation,
  parseLegacyExperience,
} from './legacy-parser';

type Mode = 'view' | 'edit';
type CropTarget = 'photo' | 'banner';

/** Snapshot per-idioma de los campos que el user edita en su CV. Cuando
 * el user cambia el toggle de idioma en el editor, hacemos snapshot del
 * form actual acá y populate del snapshot del otro idioma al form. Los
 * campos "personales" (nombre, phone, city, links) NO estan acá: se
 * comparten entre idiomas. */
interface CvLangSnapshot {
  summary: string;
  skills: string;
  soft_skills: string;
  // Skills rich text para display en el CV — separado de `skills` que
  // se usa para matching contra ofertas.
  cv_skills: string;
  experience: ExperienceEntry[] | string;
  education: EducationEntry[] | string;
}

/**
 * Mi perfil — vista LinkedIn-style con hero (banner + avatar + nombre)
 * y secciones-card de solo lectura. Toggle a modo edición para el form
 * completo. Avatar y banner pasan por un cropper modal (`<app-photo-
 * cropper-dialog>`) antes de subirse, así el usuario elige qué área
 * queda visible en lugar de subir el archivo crudo.
 */
@Component({
  selector: 'app-my-profile',
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    RouterModule,
    PhotoCropperDialogComponent,
    TextFormatToolbarComponent,
  ],
  templateUrl: './my-profile.component.html',
  styleUrl: './my-profile.component.scss',
})
export class MyProfileComponent implements OnInit {
  private countryCodeService = inject(CountryCodeService);
  private profileBuilder = inject(ProfileBuilderComponent);
  private profileService = inject(ProfileService);
  private authService = inject(AuthService);
  private router = inject(Router);
  private titleService = inject(Title);
  private http = inject(HttpClient);
  private fb = inject(FormBuilder);
  private sanitizer = inject(DomSanitizer);

  profileForm!: FormGroup;
  selectedFile: File | null = null;
  isLoading = false;
  mode = signal<Mode>('view');

  /** Gate para la card del portafolio personal. Solo admins acceden al
   *  editor. Se lee del AuthService (source of truth: JWT `is_staff`). */
  readonly isAdmin = (): boolean => this.authService.isAdmin();
  successMessage = '';
  errorMessage = '';
  countryCodes: CountryCode[] = [];
  countries = Country.getAllCountries();
  cities: any[] = [];

  /** Snapshot del último perfil traído. Fuente del view-mode. */
  profile = signal<any | null>(null);

  /**
   * Formato de edición de experience/education:
   *  - `structured`: FormArray con entries editables (empresa, cargo, fechas, etc.)
   *  - `legacy`: TextField viejo (para perfiles que aún tienen texto libre en
   *    lugar de JSON). El user puede migrar con `startStructuredMode()`.
   *
   * La decisión se hace al cargar el profile en `patchFormFromProfile`.
   */
  experienceMode = signal<'structured' | 'legacy'>('structured');
  educationMode = signal<'structured' | 'legacy'>('structured');

  /** Textos legacy (formato viejo texto libre) mostrados en modo readonly
   *  cuando el user aún no migró a estructurado. */
  legacyExperienceText = signal<string>('');
  legacyEducationText = signal<string>('');

  // ---- CV multi-idioma + preferencias de display -------------------
  /** Idioma que el user esta editando en este momento en el form.
   *  Distinto de `cv_active_language` del profile (que decide en que
   *  idioma se ve el CV renderizado). Al hacer swap del toggle,
   *  hacemos snapshot del form → snapshotFor[langActual] y populate
   *  del snapshot del nuevo lang al form. */
  cvEditingLang = signal<CvLanguage>('es');

  /** Preferencias de display del CV — se persisten al submit del
   *  profile. Aplican al render en /me VIEW y al PDF export. */
  cvTextAlign = signal<CvTextAlign>('left');
  cvFontSize = signal<CvFontSize>('md');

  /** Snapshots del contenido editable en cada idioma. El form siempre
   *  muestra los valores del `cvEditingLang` actual; el otro vive acá
   *  hasta que el user cambia el toggle o hace submit. Se inicializan
   *  desde el profile en `patchFormFromProfile`. */
  private _snapshotEs: CvLangSnapshot = this.emptySnapshot();
  private _snapshotEn: CvLangSnapshot = this.emptySnapshot();

  /** Modo actual del OTRO idioma (structured/legacy). Necesario para
   *  restaurar el modo correcto al hacer swap y no forzar structured
   *  cuando el user tiene contenido legacy en el otro idioma. */
  private _experienceModeByLang: Record<CvLanguage, 'structured' | 'legacy'> = {
    es: 'structured',
    en: 'structured',
  };
  private _educationModeByLang: Record<CvLanguage, 'structured' | 'legacy'> = {
    es: 'structured',
    en: 'structured',
  };
  private _legacyTextByLang: Record<CvLanguage, { exp: string; edu: string }> = {
    es: { exp: '', edu: '' },
    en: { exp: '', edu: '' },
  };

  /** True cuando el idioma EN aun no tiene contenido — habilita el
   *  boton "Copiar del español" en el header. */
  hasEnContent = computed(() => {
    const s = this._snapshotEn;
    const hasArrayContent = (v: ExperienceEntry[] | EducationEntry[] | string) =>
      (Array.isArray(v) && v.length > 0) || (typeof v === 'string' && v.trim() !== '');
    return (
      s.summary.trim() !== '' ||
      s.skills.trim() !== '' ||
      s.soft_skills.trim() !== '' ||
      hasArrayContent(s.experience) ||
      hasArrayContent(s.education)
    );
  });

  private emptySnapshot(): CvLangSnapshot {
    return {
      summary: '',
      skills: '',
      soft_skills: '',
      cv_skills: '',
      experience: [],
      education: [],
    };
  }

  // ---- Cropper state -------------------------------------------------
  /** Archivo seleccionado para recortar. null cierra el modal. */
  cropperFile = signal<File | null>(null);
  cropperAspect = signal(1);
  cropperRound = signal(false);
  cropperTitle = signal('Ajustar imagen');
  cropperTarget = signal<CropTarget>('photo');
  isUploadingMedia = signal(false);

  fullName = computed(() => {
    const p = this.profile();
    if (!p) return '';
    const name = `${p.first_name || ''} ${p.last_name || ''}`.trim();
    return name || 'Sin nombre';
  });

  initial = computed(() => this.fullName().charAt(0).toUpperCase() || 'U');

  photoUrl = computed(() => this.absoluteMediaUrl(this.profile()?.photo));
  bannerUrl = computed(() => this.absoluteMediaUrl(this.profile()?.banner));

  /** Idioma "vigente" del CV para el modo VIEW. Es DISTINTO de
   *  cvEditingLang (que solo aplica al form del editor): el VIEW usa
   *  siempre lo persistido en el profile (`cv_active_language`), asi
   *  refleja lo que veria un reclutador que abriera el CV publico. */
  viewLang = computed<CvLanguage>(() =>
    this.profile()?.cv_active_language === 'en' ? 'en' : 'es',
  );

  /** Labels traducidos para los headers de las secciones en el VIEW.
   *  Espeja el dict del ats-cv para consistencia visual entre las 2
   *  vistas del CV (widget en /me y PDF exportado). */
  labels = computed(() => {
    const isEn = this.viewLang() === 'en';
    return isEn
      ? {
          about: 'About me',
          experience: 'Experience',
          education: 'Education',
          skills: 'Skills',
          contact: 'Contact information',
          portfolio: 'Portfolio',
          present: 'Present',
          aboutEmpty:
            "Tell us who you are professionally. It's your presentation card to recruiters.",
          expEmpty: 'Add your work history to improve match quality.',
          eduEmpty: 'List your academic background.',
          skillsEmpty: 'Add the skills you master — comma-separated.',
          migrateExp: 'Edit your experience as blocks',
          migrateEdu: 'Edit your education as blocks',
        }
      : {
          about: 'Sobre mí',
          experience: 'Experiencia',
          education: 'Educación',
          skills: 'Habilidades',
          contact: 'Información de contacto',
          portfolio: 'Portafolio',
          present: 'Presente',
          aboutEmpty:
            'Cuenta quién eres profesionalmente. Aparece como tu carta de presentación a los reclutadores.',
          expEmpty: 'Suma tu trayectoria laboral para mejorar la calidad de los matches.',
          eduEmpty: 'Lista tu formación académica.',
          skillsEmpty: 'Agrega las skills que dominas — separadas por coma.',
          migrateExp: 'Edita tu experiencia como bloques',
          migrateEdu: 'Edita tu educación como bloques',
        };
  });

  /** Devuelve el valor de un campo del profile en el idioma vigente
   *  (o el ES como fallback si el EN esta vacio). */
  private viewFieldFor(base: string): string {
    const p = this.profile();
    if (!p) return '';
    if (this.viewLang() === 'en') {
      return p[`${base}_en`] || p[base] || '';
    }
    return p[base] || '';
  }

  /** Idem pero para experience/education que pueden ser array o string. */
  private viewEntriesFieldFor(base: 'experience' | 'education'): unknown {
    const p = this.profile();
    if (!p) return null;
    if (this.viewLang() === 'en') {
      const en = p[`${base}_en`];
      // Preferimos EN si tiene contenido — sino fallback al ES.
      if (Array.isArray(en) && en.length > 0) return en;
      if (typeof en === 'string' && en.trim() !== '') return en;
      return p[base];
    }
    return p[base];
  }

  skillsList = computed(() => {
    const raw = this.viewFieldFor('skills');
    return raw
      .split(',')
      .map((s: string) => s.trim())
      .filter(Boolean);
  });

  /** Experience como array parseado si el backend guardó JSON, sino null.
   *  Los templates de view mode lo usan para decidir entre render
   *  estructurado (empresa/cargo/fechas) vs texto libre legacy.
   *  Respeta el idioma vigente del CV. */
  experienceEntries = computed<ExperienceEntry[] | null>(() => {
    return this.tryParseEntriesFromRaw<ExperienceEntry>(this.viewEntriesFieldFor('experience'));
  });

  /** Idem para educación. */
  educationEntries = computed<EducationEntry[] | null>(() => {
    return this.tryParseEntriesFromRaw<EducationEntry>(this.viewEntriesFieldFor('education'));
  });

  /** Summary y texto legacy expuestos como getters para que el template
   *  no tenga que repetir la logica de viewFieldFor / viewEntriesFieldFor. */
  viewSummary(): string {
    return this.viewFieldFor('summary');
  }

  viewExperienceLegacy(): string {
    const v = this.viewEntriesFieldFor('experience');
    return typeof v === 'string' ? v : '';
  }

  viewEducationLegacy(): string {
    const v = this.viewEntriesFieldFor('education');
    return typeof v === 'string' ? v : '';
  }

  private tryParseEntriesFromRaw<T>(raw: unknown): T[] | null {
    if (Array.isArray(raw)) return raw as T[];
    if (typeof raw === 'string' && raw.trim().startsWith('[')) {
      try {
        const parsed: unknown = JSON.parse(raw);
        if (Array.isArray(parsed)) return parsed as T[];
      } catch {
        /* fall through */
      }
    }
    return null;
  }

  /**
   * Formatea una fecha `YYYY-MM` en español legible ("Septiembre 2025").
   * Casos especiales:
   *   - `"Actual"` (sentinel de "trabajando/cursando actualmente") → "Presente"
   *   - vacío → "" (el template no muestra el separador)
   *   - `YYYY` solo (año sin mes) → devuelve el año tal cual
   */
  formatEntryDate(value: string | undefined | null): string {
    if (!value) return '';
    if (value === 'Actual') return 'Presente';
    const match = value.match(/^(\d{4})-(\d{2})$/);
    if (!match) return value; // ya viene en otro formato — no lo tocamos
    const months = [
      'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
      'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre',
    ];
    const year = match[1];
    const monthIdx = parseInt(match[2], 10) - 1;
    const monthName = months[monthIdx] ?? '';
    return monthName ? `${monthName} ${year}` : year;
  }

  /** Construye el string de ubicación entre paréntesis: "(Bogotá, Colombia)".
   *  Devuelve string vacío si no hay ni ciudad ni país. */
  formatEntryLocation(entry: { location_city?: string; location_country?: string }): string {
    const parts: string[] = [];
    if (entry.location_city) parts.push(entry.location_city);
    if (entry.location_country) parts.push(entry.location_country);
    if (parts.length === 0) return '';
    return `(${parts.join(', ')})`;
  }

  /** Renderiza texto libre legacy en HTML seguro. Aplicaciones:
   *   - Users que guardaron su experiencia/educación como texto plano
   *     (pre-editor estructurado) suelen tener `**Empresa**` que sin
   *     este helper se ve crudo con los asteriscos.
   *   - Saltos de línea del textarea legacy se convierten a `<br>` para
   *     preservar el formato del user.
   *
   *  Seguridad: escapamos HTML primero — cualquier `<`, `>`, `&` o
   *  comilla en el texto del user queda inocuo. DESPUÉS aplicamos las
   *  transformaciones markdown-like sobre el texto ya escapado. El
   *  `bypassSecurityTrustHtml` es seguro porque el output es control
   *  nuestro, no del user. */
  renderLegacyText(raw: string | undefined | null): SafeHtml {
    if (!raw) return '';
    const escaped = raw
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
    // Bold — non-greedy para no capturar entre asteriscos separados en
    // lineas distintas ("**a** ... **b**" NO debe volverse "<strong>a
    // ... b</strong>").
    const withBold = escaped.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
    // Saltos de línea (Windows CRLF y Unix LF).
    const withBreaks = withBold.replace(/\r?\n/g, '<br>');
    return this.sanitizer.bypassSecurityTrustHtml(withBreaks);
  }

  constructor() {
    this.titleService.setTitle('SkilTak — Mi perfil');
  }

  ngOnInit(): void {
    // Empezamos con FormArray vacío en ambos — patchFormFromProfile decide
    // después si populamos entries reales o pasamos a modo legacy.
    this.profileForm = this.profileBuilder.buildProfileForm({
      education: this.fb.array([]),
      experience: this.fb.array([]),
      languages: this.fb.array([]),
    });
    this.countryCodeService.getCountryCodes().subscribe((data) => {
      this.countryCodes = data;
    });
    this.loadCurrentProfile();
  }

  // ---- FormArray helpers para experience / education ----------------

  get experienceArray(): FormArray {
    return this.profileForm.get('experience') as FormArray;
  }

  get educationArray(): FormArray {
    return this.profileForm.get('education') as FormArray;
  }

  /** Crea un FormGroup vacío para una entrada de experiencia. Los campos
   *  requeridos matchean con la interfaz `ExperienceEntry`. Fechas son
   *  `type=month` (YYYY-MM). `is_current` marca "trabajando actualmente":
   *  cuando está true, la serialización guarda `end_date = "Actual"`. */
  createExperienceGroup(entry?: Partial<ExperienceEntry> & { is_current?: boolean }): FormGroup {
    return this.fb.group({
      position: [entry?.position ?? '', Validators.required],
      company: [entry?.company ?? '', Validators.required],
      location_city: [entry?.location_city ?? ''],
      location_country: [entry?.location_country ?? ''],
      start_date: [entry?.start_date ?? '', Validators.required],
      end_date: [entry?.end_date === 'Actual' ? '' : (entry?.end_date ?? '')],
      is_current: [entry?.is_current ?? (entry?.end_date === 'Actual')],
      description: [entry?.description ?? '', Validators.required],
    });
  }

  /** Idem para educación. `is_current` = "cursando actualmente" — misma
   *  semántica que en experiencia. */
  createEducationGroup(entry?: Partial<EducationEntry> & { is_current?: boolean }): FormGroup {
    return this.fb.group({
      title: [entry?.title ?? '', Validators.required],
      institution: [entry?.institution ?? '', Validators.required],
      location_city: [entry?.location_city ?? ''],
      location_country: [entry?.location_country ?? ''],
      start_date: [entry?.start_date ?? '', Validators.required],
      end_date: [entry?.end_date === 'Actual' ? '' : (entry?.end_date ?? '')],
      is_current: [entry?.is_current ?? (entry?.end_date === 'Actual')],
    });
  }

  // ---- Languages FormArray helpers ---------------------------------

  get languagesArray(): FormArray {
    return this.profileForm.get('languages') as FormArray;
  }

  /** Crea un FormGroup para un idioma hablado. Ambos campos son
   *  requeridos porque no tiene sentido guardar filas huerfanas. */
  createLanguageGroup(entry?: Partial<LanguageEntry>): FormGroup {
    return this.fb.group({
      language: [entry?.language ?? '', Validators.required],
      level: [entry?.level ?? '', Validators.required],
    });
  }

  addLanguage(): void {
    this.languagesArray.push(this.createLanguageGroup());
  }

  removeLanguage(index: number): void {
    this.languagesArray.removeAt(index);
  }

  addExperience(): void {
    this.experienceArray.push(this.createExperienceGroup());
  }

  removeExperience(index: number): void {
    this.experienceArray.removeAt(index);
  }

  addEducation(): void {
    this.educationArray.push(this.createEducationGroup());
  }

  removeEducation(index: number): void {
    this.educationArray.removeAt(index);
  }

  /** Migra a modo estructurado desde legacy: intenta auto-parsear el
   *  texto legacy en entries (empresa, cargo, fechas, descripción). Si
   *  el parseo detecta al menos 1 entry, populamos el FormArray con lo
   *  extraído — el user solo revisa/completa lo que quedó vacío. Si el
   *  parseo NO detecta nada (formato muy libre), fallback a una entry
   *  vacía como antes.
   *  El texto legacy sigue visible como referencia en el textarea
   *  readonly de arriba, así el user puede copiar-pegar detalles
   *  puntuales si el parseo se equivocó. */
  startStructuredExperience(): void {
    this.experienceMode.set('structured');
    const parsed = parseLegacyExperience(this.legacyExperienceText());
    const groups = parsed.length > 0
      ? parsed.map((e) => this.createExperienceGroup(e))
      : [this.createExperienceGroup()];
    this.profileForm.setControl('experience', this.fb.array<FormGroup>(groups));
  }

  startStructuredEducation(): void {
    this.educationMode.set('structured');
    const parsed = parseLegacyEducation(this.legacyEducationText());
    const groups = parsed.length > 0
      ? parsed.map((e) => this.createEducationGroup(e))
      : [this.createEducationGroup()];
    this.profileForm.setControl('education', this.fb.array<FormGroup>(groups));
  }

  /** Handlers del banner promocional en modo VIEW. Combinan "entrar a
   *  edit" + "activar structured con auto-parseo" en un solo click —
   *  evitan que el user tenga que descubrir el botón "Editar como bloques"
   *  dentro del form. `queueMicrotask` da un tick al mode.set para que
   *  el rendering se actualice antes de tocar el FormArray. */
  promoteToStructuredExperience(): void {
    this.mode.set('edit');
    queueMicrotask(() => this.startStructuredExperience());
  }

  promoteToStructuredEducation(): void {
    this.mode.set('edit');
    queueMicrotask(() => this.startStructuredEducation());
  }

  /** Detecta si el valor guardado en el backend es un array estructurado
   *  (JSON stringified) o texto legacy libre. Devuelve el array parseado
   *  o null si es legacy. */
  private tryParseEntries<T>(raw: unknown): T[] | null {
    if (Array.isArray(raw)) return raw as T[];
    if (typeof raw === 'string' && raw.trim().startsWith('[')) {
      try {
        const parsed: unknown = JSON.parse(raw);
        if (Array.isArray(parsed)) return parsed as T[];
      } catch {
        /* fall through to legacy */
      }
    }
    return null;
  }

  /** Convierte una URL relativa del backend a absoluta para que el
   *  `<img>` resuelva. DRF suele devolver URL completa cuando hay
   *  request context — esto es por las dudas. */
  private absoluteMediaUrl(value: string | null | undefined): string | null {
    if (!value) return null;
    if (value.startsWith('http')) return value;
    const host = environment.apiUrl.replace(/\/api\/?$/, '');
    return `${host}${value.startsWith('/') ? '' : '/'}${value}`;
  }

  private loadCurrentProfile(): void {
    this.isLoading = true;
    this.profileService.getMyProfile().subscribe({
      next: (response) => {
        const profile = this.unwrapProfile(response);
        if (profile) {
          this.profile.set(profile);
          this.patchFormFromProfile(profile);
        }
        this.isLoading = false;
      },
      error: () => {
        this.isLoading = false;
        this.errorMessage = 'No pudimos cargar tu perfil. Prueba refrescar la página.';
      },
    });
  }

  private unwrapProfile(response: any): any | null {
    if (Array.isArray(response)) return response[0] || null;
    if (response?.results && Array.isArray(response.results)) {
      return response.results[0] || null;
    }
    if (response && typeof response === 'object' && 'first_name' in response) {
      return response;
    }
    return null;
  }

  private patchFormFromProfile(profile: any): void {
    const countryName: string = profile.country || '';
    const matchedCountry = this.countries.find(
      (c) => c.name.toLowerCase() === countryName.toLowerCase(),
    );
    const isoCode = matchedCountry?.isoCode || '';
    if (isoCode) {
      this.cities = this.profileBuilder.getCitiesByCountryCode(isoCode);
    }

    // Preferencias de display + idioma activo del CV. Se leen ANTES del
    // patch de campos editables para que el resto de la logica sepa
    // cual idioma pupular en el form.
    const activeLang: CvLanguage = profile.cv_active_language === 'en' ? 'en' : 'es';
    this.cvEditingLang.set(activeLang);
    this.cvTextAlign.set(profile.cv_text_align === 'justify' ? 'justify' : 'left');
    const validSizes: CvFontSize[] = ['sm', 'md', 'lg'];
    this.cvFontSize.set(validSizes.includes(profile.cv_font_size) ? profile.cv_font_size : 'md');

    // Snapshots iniciales: leemos los campos ES (los actuales) al
    // _snapshotEs y los campos _en al _snapshotEn. Luego populamos el
    // form con el snapshot del idioma activo.
    this._snapshotEs = this.buildSnapshotFromProfile(profile, 'es');
    this._snapshotEn = this.buildSnapshotFromProfile(profile, 'en');

    this.profileForm.patchValue({
      first_name: profile.first_name || '',
      last_name: profile.last_name || '',
      email: profile.user?.email || profile.email || '',
      number_id: profile.number_id || '',
      phone_code: profile.phone_code || '',
      phone_number: profile.phone_number || '',
      country: isoCode,
      city: profile.city || '',
      location_note: profile.location_note || '',
      professional_title: profile.professional_title || '',
      linkedin_url: profile.linkedin_url || '',
      portfolio_url: profile.portfolio_url || '',
      github_url: profile.github_url || '',
    });

    // IMPORTANTE: en el submit reemplazamos el FormArray por un
    // FormControl simple (para pasarle el JSON al profile-builder).
    // Al recargar hay que RESTAURAR el FormArray via setControl — sino
    // los helpers `experienceArray.push`/`.removeAt` fallan porque
    // `experienceArray` sigue devolviendo el FormControl del submit
    // anterior.
    //
    // El "modo por idioma" (structured/legacy) y el legacy text tambien
    // se detectan aca por-idioma. Populamos el FORM con el snapshot
    // del idioma ACTIVO — el otro queda en su almacenamiento hasta que
    // el user cambie el toggle o haga submit.
    this._experienceModeByLang.es = this.detectMode(profile.experience);
    this._experienceModeByLang.en = this.detectMode(profile.experience_en);
    this._educationModeByLang.es = this.detectMode(profile.education);
    this._educationModeByLang.en = this.detectMode(profile.education_en);
    this._legacyTextByLang.es = {
      exp: this._experienceModeByLang.es === 'legacy' ? String(profile.experience || '') : '',
      edu: this._educationModeByLang.es === 'legacy' ? String(profile.education || '') : '',
    };
    this._legacyTextByLang.en = {
      exp: this._experienceModeByLang.en === 'legacy' ? String(profile.experience_en || '') : '',
      edu: this._educationModeByLang.en === 'legacy' ? String(profile.education_en || '') : '',
    };

    this.applySnapshotToForm(activeLang);

    // Idiomas: el backend guarda como JSON string en un TextField, pero
    // el form los consume como FormArray de {language, level}. Parseamos
    // si viene string, o usamos el array directo si el serializer ya lo
    // devolvió parseado.
    this.hydrateLanguagesFromProfile(profile.languages);
  }

  /** Parse-y-populate del FormArray de idiomas desde el profile crudo.
   *  Cubre los 3 shapes posibles del backend: array parseado, JSON string
   *  o null/vacio. */
  private hydrateLanguagesFromProfile(raw: unknown): void {
    let entries: LanguageEntry[] = [];
    if (Array.isArray(raw)) {
      entries = raw as LanguageEntry[];
    } else if (typeof raw === 'string' && raw.trim().startsWith('[')) {
      try {
        const parsed: unknown = JSON.parse(raw);
        if (Array.isArray(parsed)) entries = parsed as LanguageEntry[];
      } catch {
        /* raw invalido — dejamos vacio */
      }
    }
    const array = this.fb.array<FormGroup>(
      entries
        .filter((e) => e && typeof e.language === 'string' && e.language.trim() !== '')
        .map((e) => this.createLanguageGroup(e)),
    );
    this.profileForm.setControl('languages', array);
  }

  /** Detecta el modo (structured / legacy) de un campo experience o
   *  education. Structured = array o JSON-string de array. Legacy =
   *  string vacio (arranca structured) o texto libre. */
  private detectMode(raw: unknown): 'structured' | 'legacy' {
    const entries = this.tryParseEntries<any>(raw);
    if (entries !== null) return 'structured';
    if (typeof raw === 'string' && raw.trim() !== '') return 'legacy';
    return 'structured';
  }

  /** Extrae un CvLangSnapshot desde el profile crudo del backend para
   *  el idioma pedido. `es` lee summary/skills/etc; `en` lee summary_en/
   *  skills_en/etc. Los arrays se parsean; el texto legacy se preserva
   *  como string. */
  private buildSnapshotFromProfile(profile: any, lang: CvLanguage): CvLangSnapshot {
    const key = (base: string) => (lang === 'es' ? base : `${base}_en`);
    const rawExp = profile[key('experience')];
    const rawEdu = profile[key('education')];
    const expEntries = this.tryParseEntries<ExperienceEntry>(rawExp);
    const eduEntries = this.tryParseEntries<EducationEntry>(rawEdu);
    return {
      summary: profile[key('summary')] || '',
      skills: profile[key('skills')] || '',
      soft_skills: profile[key('soft_skills')] || '',
      cv_skills: profile[key('cv_skills')] || '',
      experience: expEntries !== null ? expEntries : (typeof rawExp === 'string' ? rawExp : ''),
      education: eduEntries !== null ? eduEntries : (typeof rawEdu === 'string' ? rawEdu : ''),
    };
  }

  onCountryChange(countryCode: string): void {
    const phone = this.profileBuilder.extractPhoneCode(this.countries, countryCode);
    this.profileForm.patchValue({ phone_code: phone });
    this.cities = this.profileBuilder.getCitiesByCountryCode(countryCode);
  }

  onFileSelected(event: any) {
    this.selectedFile = event.target.files[0];
  }

  // ---- Cropper triggers ---------------------------------------------

  /**
   * Abre el cropper en modo avatar: cuadrado, preview redondo. El
   * archivo crudo va al dialog; cuando el usuario aplica, recibimos
   * el blob recortado y lo subimos como `photo`.
   */
  onPhotoFileSelected(event: Event): void {
    const file = (event.target as HTMLInputElement).files?.[0];
    if (!file) return;
    this.cropperFile.set(file);
    this.cropperAspect.set(1);
    this.cropperRound.set(true);
    this.cropperTitle.set('Ajustar foto de perfil');
    this.cropperTarget.set('photo');
    (event.target as HTMLInputElement).value = '';
  }

  /**
   * Abre el cropper en modo banner: rectángulo ancho 4:1, preview
   * cuadrado clásico (no redondo).
   */
  onBannerFileSelected(event: Event): void {
    const file = (event.target as HTMLInputElement).files?.[0];
    if (!file) return;
    this.cropperFile.set(file);
    this.cropperAspect.set(4);
    this.cropperRound.set(false);
    this.cropperTitle.set('Ajustar imagen del banner');
    this.cropperTarget.set('banner');
    (event.target as HTMLInputElement).value = '';
  }

  /**
   * Re-abre el cropper con la imagen YA SUBIDA — para que el user pueda
   * re-zoomear o re-centrar sin tener que volver a elegir el archivo
   * desde el disco.
   *
   * Estrategia: fetch del URL público → blob → File. La imagen ya está
   * en nuestro dominio (cropped al output previo) así que no hay CORS.
   * El crop sucesivo opera sobre el ya-recortado — perdés algo de
   * resolución si re-zoomeás muy de cerca, pero la salida (1024 avatar
   * / 1920 banner) sigue siendo retina-ready en la mayoría de los casos.
   */
  editExistingImage(target: CropTarget): void {
    const url = target === 'photo' ? this.photoUrl() : this.bannerUrl();
    if (!url) return;
    this.isUploadingMedia.set(true);
    fetch(url)
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.blob();
      })
      .then((blob) => {
        const ext = blob.type === 'image/png' ? 'png' : 'jpg';
        const file = new File([blob], `${target}-current.${ext}`, { type: blob.type });
        this.cropperFile.set(file);
        if (target === 'photo') {
          this.cropperAspect.set(1);
          this.cropperRound.set(true);
          this.cropperTitle.set('Reajustar foto de perfil');
        } else {
          this.cropperAspect.set(4);
          this.cropperRound.set(false);
          this.cropperTitle.set('Reajustar imagen del banner');
        }
        this.cropperTarget.set(target);
        this.isUploadingMedia.set(false);
      })
      .catch(() => {
        this.isUploadingMedia.set(false);
        this.errorMessage = 'No pudimos abrir la imagen actual para ajustarla.';
        setTimeout(() => (this.errorMessage = ''), 4000);
      });
  }

  onCropperApplied(blob: Blob): void {
    const target = this.cropperTarget();
    const ext = blob.type === 'image/png' ? 'png' : 'jpg';
    const filename = `${target}.${ext}`;
    this.uploadMedia(target, blob, filename);
  }

  onCropperCancelled(): void {
    this.cropperFile.set(null);
  }

  /**
   * POST aparte que solo manda el campo correspondiente (`photo` o
   * `banner`). No pasa por la validación del form porque la idea es
   * que el usuario pueda cambiar la imagen sin entrar al modo edición.
   */
  private uploadMedia(target: CropTarget, blob: Blob, filename: string): void {
    this.isUploadingMedia.set(true);
    const formData = new FormData();
    formData.append(target, blob, filename);

    const token = localStorage.getItem(STORAGE_KEYS.ACCESS_TOKEN);
    const headers = new HttpHeaders({ Authorization: `Bearer ${token}` });

    this.http.post<any>(`${environment.apiUrl}/users/profiles/`, formData, { headers }).subscribe({
      next: (res) => {
        this.isUploadingMedia.set(false);
        this.cropperFile.set(null);
        // Refrescar solo el field que cambió
        this.profile.update((p) => ({ ...(p || {}), [target]: res[target] }));
        this.successMessage = target === 'photo' ? 'Foto actualizada.' : 'Banner actualizado.';
        setTimeout(() => (this.successMessage = ''), 2500);
      },
      error: () => {
        this.isUploadingMedia.set(false);
        this.cropperFile.set(null);
        this.errorMessage = 'No pudimos subir la imagen. Verifica el formato (JPG/PNG).';
        setTimeout(() => (this.errorMessage = ''), 4000);
      },
    });
  }

  onSubmit() {
    // Antes de enviar: aplicar el flag `is_current` a las entries y
    // ajustar los controles de experience/education según el modo.
    // El profile-builder es agnóstico al modo — detecta array vs string
    // y actúa; nosotros nada más preparamos el form para que llegue en
    // la forma correcta.
    this.prepareEntriesBeforeSubmit();

    this.profileBuilder.submitProfileData(
      this.profileForm,
      this.selectedFile,
      () => {
        this.isLoading = true;
        this.successMessage = '';
        this.errorMessage = '';
      },
      () => {
        this.isLoading = false;
        this.successMessage = 'Cambios guardados.';
        this.authService.updateProfileStatus();
        this.mode.set('view');
        this.loadCurrentProfile();
      },
      () => {
        this.isLoading = false;
        this.errorMessage = 'No pudimos guardar los cambios. Inténtalo nuevamente.';
      },
      false,
    );
  }

  /**
   * Prepara el form para el submit:
   *  - Snapshot del form actual → snapshot del idioma activo (asi
   *    tenemos AMBOS snapshots (ES y EN) al dia antes de mandar).
   *  - Agrega al FormGroup los campos del OTRO idioma como controles
   *    con sufijo `_en` (o `_en` vacio si estamos editando ES y el
   *    snapshot EN no cambio) — profile-builder los envia todos en el
   *    loop generico.
   *  - Agrega las 3 preferencias de display (cv_active_language,
   *    cv_text_align, cv_font_size).
   *  - Reemplaza el FormArray de experience/education del IDIOMA ACTIVO
   *    por un control simple con array/string listo para persistir.
   */
  private prepareEntriesBeforeSubmit(): void {
    // 1) Snapshot del form → snapshot del idioma activo.
    const currentLang = this.cvEditingLang();
    this.captureFormToSnapshot(currentLang);

    // 2) Consolidamos ambos snapshots en controles del form. Los
    //    campos ES se llaman igual que hoy (summary, skills, etc); los
    //    EN llevan sufijo _en. profile-builder itera todo el rawData
    //    del form y hace formData.append(key, value) para los que no
    //    son experience/education.
    const es = this._snapshotEs;
    const en = this._snapshotEn;

    this.profileForm.setControl('summary', this.fb.control(es.summary, Validators.required));
    this.profileForm.setControl('skills', this.fb.control(es.skills, Validators.required));
    this.setOrAddControl('soft_skills', es.soft_skills);
    this.setOrAddControl('cv_skills', es.cv_skills);
    this.setOrAddControl('summary_en', en.summary);
    this.setOrAddControl('skills_en', en.skills);
    this.setOrAddControl('soft_skills_en', en.soft_skills);
    this.setOrAddControl('cv_skills_en', en.cv_skills);

    // 3) Experience/education del idioma ACTIVO — mismo patron que
    //    antes: array o string legacy segun el modo.
    this.profileForm.setControl(
      'experience',
      this.fb.control(this.serializeEntriesForSubmit(es.experience)),
    );
    this.profileForm.setControl(
      'education',
      this.fb.control(this.serializeEntriesForSubmit(es.education)),
    );

    // 4) Experience/education del OTRO idioma como campos _en. Los
    //    mandamos SIEMPRE (aunque el user no los haya editado) para no
    //    perder contenido previamente guardado — el snapshot EN se
    //    inicializa desde el profile en el load.
    this.setOrAddControl(
      'experience_en',
      this.serializeEntriesForSubmitAsString(en.experience),
    );
    this.setOrAddControl(
      'education_en',
      this.serializeEntriesForSubmitAsString(en.education),
    );

    // 5) Preferencias de display del CV.
    this.setOrAddControl('cv_active_language', this.cvEditingLang());
    this.setOrAddControl('cv_text_align', this.cvTextAlign());
    this.setOrAddControl('cv_font_size', this.cvFontSize());
  }

  private setOrAddControl(name: string, value: unknown): void {
    if (this.profileForm.contains(name)) {
      this.profileForm.setControl(name, this.fb.control(value));
    } else {
      this.profileForm.addControl(name, this.fb.control(value));
    }
  }

  /** Devuelve el array o el string legacy tal cual para que
   *  profile-builder decida el shape del formData (JSON.stringify si es
   *  array, string plano si es legacy). */
  private serializeEntriesForSubmit(entries: ExperienceEntry[] | EducationEntry[] | string): unknown {
    if (Array.isArray(entries)) return entries;
    return entries || '';
  }

  /** Version que SIEMPRE serializa a string — necesario para los campos
   *  _en que van por el loop generico de profile-builder (que hace
   *  String(value)). Los arrays se convierten a JSON. */
  private serializeEntriesForSubmitAsString(
    entries: ExperienceEntry[] | EducationEntry[] | string,
  ): string {
    if (Array.isArray(entries)) {
      return entries.length === 0 ? '' : JSON.stringify(entries);
    }
    return entries || '';
  }

  toggleEdit(): void {
    this.mode.update((m) => (m === 'view' ? 'edit' : 'view'));
    this.successMessage = '';
    this.errorMessage = '';
  }

  // ═══════════════════════════════════════════════════════════════════
  // CV multi-idioma — swap del form, copy ES→EN, y setters de display
  // ═══════════════════════════════════════════════════════════════════

  /** Cambia el idioma activo del editor. Guarda snapshot del form
   *  actual al lang saliente y populate del snapshot del lang entrante
   *  al form. Sin esto, cambiar idioma perdía el trabajo del user en
   *  el idioma anterior si no había pasado por submit. */
  switchEditingLang(next: CvLanguage): void {
    const current = this.cvEditingLang();
    if (current === next) return;

    // 1) Snapshot del form actual → snapshot del lang saliente.
    this.captureFormToSnapshot(current);

    // 2) Populate del form desde el snapshot del lang entrante.
    this.cvEditingLang.set(next);
    this.applySnapshotToForm(next);
  }

  /** Copia el contenido del snapshot ES al snapshot EN (y al form si
   *  el user esta editando EN). Uso tipico: user acaba de activar EN
   *  por primera vez, quiere arrancar con el contenido ES y traducirlo
   *  manualmente en vez de escribir de cero. Sobrescribe cualquier
   *  contenido EN previo — no es reversible. */
  copyEsContentToEn(): void {
    // Aseguramos que el snapshotEs este al dia si el user esta en ES.
    if (this.cvEditingLang() === 'es') {
      this.captureFormToSnapshot('es');
    }
    // Clonamos structuredClone para arrays (evita alias entre snapshots).
    this._snapshotEn = {
      summary: this._snapshotEs.summary,
      skills: this._snapshotEs.skills,
      soft_skills: this._snapshotEs.soft_skills,
      cv_skills: this._snapshotEs.cv_skills,
      experience: Array.isArray(this._snapshotEs.experience)
        ? this._snapshotEs.experience.map((e) => ({ ...e }))
        : this._snapshotEs.experience,
      education: Array.isArray(this._snapshotEs.education)
        ? this._snapshotEs.education.map((e) => ({ ...e }))
        : this._snapshotEs.education,
    };
    this._experienceModeByLang.en = this._experienceModeByLang.es;
    this._educationModeByLang.en = this._educationModeByLang.es;
    this._legacyTextByLang.en = { ...this._legacyTextByLang.es };
    // Si el user esta editando EN, refrescamos el form para que vea el
    // copy inmediatamente.
    if (this.cvEditingLang() === 'en') {
      this.applySnapshotToForm('en');
    }
  }

  setCvTextAlign(align: CvTextAlign): void {
    this.cvTextAlign.set(align);
  }

  setCvFontSize(size: CvFontSize): void {
    this.cvFontSize.set(size);
  }

  /** Snapshot del estado actual del form → almacen del idioma indicado.
   *  Cubre los 5 campos que el user edita: summary, skills, soft_skills,
   *  experience (array/legacy), education (array/legacy). El resto de
   *  campos (nombre, phone, city, links) son shared. */
  private captureFormToSnapshot(lang: CvLanguage): void {
    const snapshot: CvLangSnapshot = {
      summary: this.profileForm.get('summary')?.value ?? '',
      skills: this.profileForm.get('skills')?.value ?? '',
      soft_skills: this.profileForm.get('soft_skills')?.value ?? '',
      cv_skills: this.profileForm.get('cv_skills')?.value ?? '',
      experience: this.snapshotExperienceFromForm(),
      education: this.snapshotEducationFromForm(),
    };
    if (lang === 'es') {
      this._snapshotEs = snapshot;
    } else {
      this._snapshotEn = snapshot;
    }
    // Guardar el modo tambien (structured vs legacy) para restaurar
    // correctamente al hacer swap.
    this._experienceModeByLang[lang] = this.experienceMode();
    this._educationModeByLang[lang] = this.educationMode();
    this._legacyTextByLang[lang] = {
      exp: this.legacyExperienceText(),
      edu: this.legacyEducationText(),
    };
  }

  private snapshotExperienceFromForm(): ExperienceEntry[] | string {
    if (this.experienceMode() === 'legacy') {
      return this.legacyExperienceText();
    }
    // Structured: leer FormArray y limpiar `is_current` sentinel.
    return this.experienceArray.value.map((e: any) => ({
      position: e.position,
      company: e.company,
      location_city: e.location_city || '',
      location_country: e.location_country || '',
      start_date: e.start_date,
      end_date: e.is_current ? 'Actual' : (e.end_date || ''),
      description: e.description,
    })) as ExperienceEntry[];
  }

  private snapshotEducationFromForm(): EducationEntry[] | string {
    if (this.educationMode() === 'legacy') {
      return this.legacyEducationText();
    }
    return this.educationArray.value.map((e: any) => ({
      title: e.title,
      institution: e.institution,
      location_city: e.location_city || '',
      location_country: e.location_country || '',
      start_date: e.start_date,
      end_date: e.is_current ? 'Actual' : (e.end_date || ''),
    })) as EducationEntry[];
  }

  /** Populate del form desde el snapshot del idioma indicado. Restaura
   *  tambien el modo (structured/legacy) y el legacy text. */
  private applySnapshotToForm(lang: CvLanguage): void {
    const snap = lang === 'es' ? this._snapshotEs : this._snapshotEn;
    this.profileForm.patchValue({
      summary: snap.summary,
      skills: snap.skills,
      soft_skills: snap.soft_skills,
      cv_skills: snap.cv_skills,
    });

    // Experience mode + content
    const expMode = this._experienceModeByLang[lang];
    this.experienceMode.set(expMode);
    if (expMode === 'legacy') {
      this.legacyExperienceText.set(this._legacyTextByLang[lang].exp);
      this.profileForm.setControl(
        'experience',
        this.fb.control(this._legacyTextByLang[lang].exp, Validators.required),
      );
    } else {
      const entries = Array.isArray(snap.experience) ? snap.experience : [];
      const array = this.fb.array<FormGroup>([]);
      if (entries.length === 0) {
        array.push(this.createExperienceGroup());
      } else {
        entries.forEach((e) => array.push(this.createExperienceGroup(e)));
      }
      this.profileForm.setControl('experience', array);
      this.legacyExperienceText.set('');
    }

    // Education mode + content
    const eduMode = this._educationModeByLang[lang];
    this.educationMode.set(eduMode);
    if (eduMode === 'legacy') {
      this.legacyEducationText.set(this._legacyTextByLang[lang].edu);
      this.profileForm.setControl(
        'education',
        this.fb.control(this._legacyTextByLang[lang].edu, Validators.required),
      );
    } else {
      const entries = Array.isArray(snap.education) ? snap.education : [];
      const array = this.fb.array<FormGroup>([]);
      if (entries.length === 0) {
        array.push(this.createEducationGroup());
      } else {
        entries.forEach((e) => array.push(this.createEducationGroup(e)));
      }
      this.profileForm.setControl('education', array);
      this.legacyEducationText.set('');
    }
  }

  goToDashboard(): void {
    this.router.navigate(['/dashboard']);
  }
}

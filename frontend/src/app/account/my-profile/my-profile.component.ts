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
import { EducationEntry, ExperienceEntry } from '../../models/profile.model';

type Mode = 'view' | 'edit';
type CropTarget = 'photo' | 'banner';

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

  skillsList = computed(() => {
    const raw = this.profile()?.skills || '';
    return raw
      .split(',')
      .map((s: string) => s.trim())
      .filter(Boolean);
  });

  /** Experience como array parseado si el backend guardó JSON, sino null.
   *  Los templates de view mode lo usan para decidir entre render
   *  estructurado (empresa/cargo/fechas) vs texto libre legacy. */
  experienceEntries = computed<ExperienceEntry[] | null>(() => {
    return this.tryParseEntriesFromRaw<ExperienceEntry>(this.profile()?.experience);
  });

  /** Idem para educación. */
  educationEntries = computed<EducationEntry[] | null>(() => {
    return this.tryParseEntriesFromRaw<EducationEntry>(this.profile()?.education);
  });

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

  /** Migra a modo estructurado desde legacy: reemplaza el textarea viejo
   *  (que en el form vive como FormControl string) por un FormArray
   *  fresco + una entrada en blanco lista para llenar. El texto legacy
   *  queda en pantalla como referencia hasta que el user guarde. */
  startStructuredExperience(): void {
    this.experienceMode.set('structured');
    this.profileForm.setControl('experience', this.fb.array<FormGroup>([this.createExperienceGroup()]));
  }

  startStructuredEducation(): void {
    this.educationMode.set('structured');
    this.profileForm.setControl('education', this.fb.array<FormGroup>([this.createEducationGroup()]));
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

    this.profileForm.patchValue({
      first_name: profile.first_name || '',
      last_name: profile.last_name || '',
      email: profile.user?.email || profile.email || '',
      number_id: profile.number_id || '',
      phone_code: profile.phone_code || '',
      phone_number: profile.phone_number || '',
      country: isoCode,
      city: profile.city || '',
      professional_title: profile.professional_title || '',
      summary: profile.summary || '',
      skills: profile.skills || '',
      linkedin_url: profile.linkedin_url || '',
      portfolio_url: profile.portfolio_url || '',
    });

    // IMPORTANTE: en el submit reemplazamos el FormArray por un
    // FormControl simple (para pasarle el JSON al profile-builder).
    // Al recargar hay que RESTAURAR el FormArray via setControl — sino
    // los helpers `experienceArray.push`/`.removeAt` fallan porque
    // `experienceArray` sigue devolviendo el FormControl del submit
    // anterior.

    // Experience
    const expArray = this.fb.array<FormGroup>([]);
    const expEntries = this.tryParseEntries<ExperienceEntry>(profile.experience);
    if (expEntries !== null) {
      this.experienceMode.set('structured');
      if (expEntries.length === 0) {
        expArray.push(this.createExperienceGroup());
      } else {
        expEntries.forEach((e) => expArray.push(this.createExperienceGroup(e)));
      }
      this.legacyExperienceText.set('');
    } else {
      const text = typeof profile.experience === 'string' ? profile.experience : '';
      if (text.trim() === '') {
        this.experienceMode.set('structured');
        expArray.push(this.createExperienceGroup());
        this.legacyExperienceText.set('');
      } else {
        this.experienceMode.set('legacy');
        this.legacyExperienceText.set(text);
      }
    }
    this.profileForm.setControl('experience', expArray);

    // Education (misma lógica)
    const eduArray = this.fb.array<FormGroup>([]);
    const eduEntries = this.tryParseEntries<EducationEntry>(profile.education);
    if (eduEntries !== null) {
      this.educationMode.set('structured');
      if (eduEntries.length === 0) {
        eduArray.push(this.createEducationGroup());
      } else {
        eduEntries.forEach((e) => eduArray.push(this.createEducationGroup(e)));
      }
      this.legacyEducationText.set('');
    } else {
      const text = typeof profile.education === 'string' ? profile.education : '';
      if (text.trim() === '') {
        this.educationMode.set('structured');
        eduArray.push(this.createEducationGroup());
        this.legacyEducationText.set('');
      } else {
        this.educationMode.set('legacy');
        this.legacyEducationText.set(text);
      }
    }
    this.profileForm.setControl('education', eduArray);
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
   *  - Modo legacy: reemplaza el control por el string legacy tal cual
   *    (para que profile-builder detecte que es texto libre).
   *  - Modo estructurado: transforma cada entry aplicando el sentinel
   *    `end_date = "Actual"` cuando `is_current: true`, y elimina el
   *    campo `is_current` que no forma parte de la interfaz persistida.
   */
  private prepareEntriesBeforeSubmit(): void {
    // Experience
    if (this.experienceMode() === 'legacy') {
      this.profileForm.setControl(
        'experience',
        this.fb.control(this.legacyExperienceText(), Validators.required),
      );
    } else {
      const cleaned = this.experienceArray.value.map((e: any) => ({
        position: e.position,
        company: e.company,
        location_city: e.location_city || '',
        location_country: e.location_country || '',
        start_date: e.start_date,
        end_date: e.is_current ? 'Actual' : (e.end_date || ''),
        description: e.description,
      }));
      // Reemplazamos el FormArray por un control simple con el array
      // limpio — profile-builder lo detectará como array y hará el
      // JSON.stringify.
      this.profileForm.setControl('experience', this.fb.control(cleaned));
    }
    // Education
    if (this.educationMode() === 'legacy') {
      this.profileForm.setControl(
        'education',
        this.fb.control(this.legacyEducationText(), Validators.required),
      );
    } else {
      const cleaned = this.educationArray.value.map((e: any) => ({
        title: e.title,
        institution: e.institution,
        location_city: e.location_city || '',
        location_country: e.location_country || '',
        start_date: e.start_date,
        end_date: e.is_current ? 'Actual' : (e.end_date || ''),
      }));
      this.profileForm.setControl('education', this.fb.control(cleaned));
    }
  }

  toggleEdit(): void {
    this.mode.update((m) => (m === 'view' ? 'edit' : 'view'));
    this.successMessage = '';
    this.errorMessage = '';
  }

  goToDashboard(): void {
    this.router.navigate(['/dashboard']);
  }
}

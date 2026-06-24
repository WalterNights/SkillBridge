import { Country } from 'country-state-city';
import { CommonModule } from '@angular/common';
import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { Title } from '@angular/platform-browser';
import { FormGroup, ReactiveFormsModule } from '@angular/forms';
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

  constructor() {
    this.titleService.setTitle('SkilTak — Mi perfil');
  }

  ngOnInit(): void {
    this.profileForm = this.profileBuilder.buildProfileForm();
    this.countryCodeService.getCountryCodes().subscribe((data) => {
      this.countryCodes = data;
    });
    this.loadCurrentProfile();
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
        this.errorMessage = 'No pudimos cargar tu perfil. Probá refrescar la página.';
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
      education: profile.education || '',
      skills: profile.skills || '',
      experience: profile.experience || '',
      linkedin_url: profile.linkedin_url || '',
      portfolio_url: profile.portfolio_url || '',
    });
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
        this.errorMessage = 'No pudimos subir la imagen. Verificá el formato (JPG/PNG).';
        setTimeout(() => (this.errorMessage = ''), 4000);
      },
    });
  }

  onSubmit() {
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
        this.errorMessage = 'No pudimos guardar los cambios. Intentalo nuevamente.';
      },
      false,
    );
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

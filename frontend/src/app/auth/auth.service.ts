import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { tap, BehaviorSubject, Observable, throwError } from 'rxjs';
import { environment } from '../../environment/environment';
import { StorageMethodComponent } from '../shared/storage-method/storage-method';

interface RegisterData {
  username: string;
  email: string;
  password: string;
}

/** Tipo de cuenta. Refleja el backend `User.account_type`.
 *  Mantenido en union (no enum) para que pueda llegar como string del
 *  JWT sin coerciones raras. */
export type AccountType = 'professional' | 'company';

/** Payload del POST /api/companies/register/ — matchea el serializer
 *  CompanyRegisterSerializer del backend. */
export interface CompanyRegisterData {
  email: string;
  password: string;
  legal_name: string;
  country?: string;
  city?: string;
  industry?: string;
  website?: string;
  size?: string;
  short_description?: string;
  responsible_name: string;
  responsible_role: string;
  responsible_email: string;
}

@Injectable({
  providedIn: 'root',
})
export class AuthService {
  private apiUrl = `${environment.apiUrl}/users/register/`;
  private isLoggedInSubject = new BehaviorSubject<boolean>(!!this.getToken());
  isLoggedIn$ = this.isLoggedInSubject.asObservable();
  private isProfileCompleteSubject = new BehaviorSubject<boolean>(this.getProfileStatus());
  isProfileComplete$ = this.isProfileCompleteSubject.asObservable();
  private isAdminSubject = new BehaviorSubject<boolean>(this.getIsAdmin());
  /** True si el user tiene is_staff=True en Django. Lo escupe el endpoint
   *  de login y lo cacheamos en storage; se actualiza solo al re-loguear.
   *  Si cambia el rol en backend mientras el user tiene sesión activa, no
   *  se refresca hasta el próximo login — aceptable para v1 (cambios de
   *  rol son raros). */
  isAdmin$ = this.isAdminSubject.asObservable();

  /** Tipo de cuenta — `professional` (busca ofertas) o `company` (busca
   *  perfiles). Misma mecánica que `isAdmin`: viene en el JWT payload,
   *  se cachea en storage, se refresca al re-loguear. */
  private accountTypeSubject = new BehaviorSubject<AccountType>(
    this.getAccountType(),
  );
  accountType$ = this.accountTypeSubject.asObservable();

  StorageKey = [
    'access_token',
    'refresh_token',
    'storage',
    'user',
    'user_id',
    'user_name',
    'professional_title',
    'profile_photo',
    'is_profile_complete',
    'is_staff',
    'account_type',
    'manual_profile_draft',
  ];
  storage: 'session' | 'local' = 'session';

  constructor(
    private http: HttpClient,
    private storageMethod: StorageMethodComponent,
  ) {
    // BUG fix: el `this.storage` solo se inicializaba dentro de
    // login(). Cuando el user reabría el browser, no había login (ya
    // estaba autenticado por localStorage), entonces `this.storage`
    // quedaba en 'session' default. Al expirar el JWT y refrescarlo,
    // escribíamos el nuevo token en sessionStorage en vez de
    // localStorage → al cerrar browser, sesión perdida pese a
    // tener "Mantener sesión iniciada" prendido.
    this.storage = localStorage.getItem('storage') === 'true' ? 'local' : 'session';
  }

  getToken(): string | null {
    if (localStorage.getItem('storage') === 'true') {
      return localStorage.getItem('access_token');
    } else {
      return sessionStorage.getItem('access_token');
    }
  }

  private getProfileStatus(): boolean {
    if (localStorage.getItem('storage') === 'true') {
      return localStorage.getItem('is_profile_complete') === 'true';
    } else {
      return sessionStorage.getItem('is_profile_complete') === 'true';
    }
  }

  /** Lee el flag de admin (Django `is_staff`) cacheado en storage al
   *  login. Devuelve false ante cualquier ausencia/parsing fallido —
   *  jamás escalar permisos por defecto. */
  private getIsAdmin(): boolean {
    if (localStorage.getItem('storage') === 'true') {
      return localStorage.getItem('is_staff') === 'true';
    }
    return sessionStorage.getItem('is_staff') === 'true';
  }

  /** Snapshot sincrónico del flag — usado por guards / sidebar. Los
   *  consumidores reactivos pueden suscribirse a `isAdmin$`. */
  isAdmin(): boolean {
    return this.getIsAdmin();
  }

  /** Lee el account_type cacheado. Default `professional` si no está
   *  set — coincide con el default del backend y mantiene back-compat
   *  con sesiones previas al feature de empresa. */
  private getAccountType(): AccountType {
    const useLocal = localStorage.getItem('storage') === 'true';
    const raw = useLocal
      ? localStorage.getItem('account_type')
      : sessionStorage.getItem('account_type');
    return raw === 'company' ? 'company' : 'professional';
  }

  /** Snapshot sincrónico — usado por guards y router redirects. Para
   *  binding reactivo, suscribirse a `accountType$`. */
  accountType(): AccountType {
    return this.getAccountType();
  }

  isCompany(): boolean {
    return this.getAccountType() === 'company';
  }

  isProfessional(): boolean {
    return this.getAccountType() === 'professional';
  }

  /** Ruta home según account_type. Usada por:
   *   - el redirect post-login
   *   - el AutoGuard cuando el user logueado entra a una ruta raíz
   *   - el AdminGuard / CompanyGuard al rechazar acceso cross-type
   *
   *  Profesional con `is_profile_complete=false` se manda al wizard
   *  /profile como hoy. Para empresa el wizard equivalente se setea
   *  durante el registro (form único), así que va directo a su
   *  dashboard.
   */
  homeRouteForAccountType(): string {
    if (this.isCompany()) return '/company/dashboard';
    return '/dashboard';
  }

  updateProfileStatus(): void {
    const status = this.getProfileStatus();
    this.isProfileCompleteSubject.next(status);
  }

  syncAuthStatus(): void {
    this.isLoggedInSubject.next(!!this.getToken());
  }

  isAuthenticated(): boolean {
    return !!this.getToken();
  }

  /**
   * Read the user's display name honoring the storage preference.
   * Returns the explicit 'Usuario' fallback when no session is set
   * so the UI never shows an empty avatar/label.
   */
  getUserName(): string {
    const useLocal = localStorage.getItem('storage') === 'true';
    const value = useLocal
      ? localStorage.getItem('user_name')
      : sessionStorage.getItem('user_name');
    return value ?? 'Usuario';
  }

  /**
   * Read the user's email. `user_email` is always written to
   * sessionStorage at login time, regardless of "remember me".
   */
  getUserEmail(): string {
    return sessionStorage.getItem('user_email') ?? '';
  }

  /**
   * Read the user's professional title (e.g. "Senior Backend Developer").
   * Used by the AppShell tip widget to fetch tips relevant to the user's
   * vertical without an extra request to /profiles/. Returns '' when
   * unknown so callers can fall back to universal tips.
   */
  getProfessionalTitle(): string {
    const useLocal = localStorage.getItem('storage') === 'true';
    const value = useLocal
      ? localStorage.getItem('professional_title')
      : sessionStorage.getItem('professional_title');
    return value ?? '';
  }

  /**
   * URL absoluta de la foto de perfil del user para el avatar del topbar.
   * Vacío si el user no subió foto o el cliente todavía no recibió el
   * dato (login muy viejo previo a la feature). El consumidor cae al
   * initial cuando esto está vacío.
   *
   * Limitación conocida: el valor se cachea desde el login. Si el user
   * sube una foto nueva en /me, va a ver el initial (o la foto vieja)
   * hasta el próximo login. Aceptable para v1 — agregar un setter via
   * Subject cuando empiece a molestar.
   */
  getProfilePhotoUrl(): string {
    const useLocal = localStorage.getItem('storage') === 'true';
    const value = useLocal
      ? localStorage.getItem('profile_photo')
      : sessionStorage.getItem('profile_photo');
    return value ?? '';
  }

  register(data: RegisterData): Observable<any> {
    return this.http.post(this.apiUrl, data);
  }

  /** POST /api/companies/register/ — registro de cuenta empresa.
   *  Sigue el mismo patrón que `register()`: NO loguea automáticamente;
   *  el componente redirige a /auth/login tras 201.
   */
  registerCompany(data: CompanyRegisterData): Observable<any> {
    return this.http.post(`${environment.apiUrl}/companies/register/`, data);
  }

  /**
   * @param remember Si true, persiste el token en localStorage para
   *   sobrevivir el cierre del browser. Si false (default), va a
   *   sessionStorage y la sesión muere al cerrar la pestaña.
   *   El login.component pasa el valor del switch "Mantener sesión
   *   iniciada"; sin el parámetro asume false para compatibilidad
   *   con callers viejos.
   */
  login(credentials: { username: string; password: string }, remember: boolean = false) {
    return this.http.post(`${environment.apiUrl}/token/login/`, credentials).pipe(
      tap((res: any) => {
        // Persistimos la preferencia primero — getToken() y todos los
        // getters consultan localStorage.getItem('storage') después.
        if (remember) {
          localStorage.setItem('storage', 'true');
        } else {
          localStorage.removeItem('storage');
        }

        // Limpiamos los tokens del storage OPUESTO antes de escribir
        // en el elegido. Sin esto, si el user logueó antes con
        // remember=ON y ahora con OFF, los tokens viejos quedaban
        // huérfanos en localStorage — riesgo de privacidad en compus
        // compartidas.
        const oppositeStorage: 'session' | 'local' = remember ? 'session' : 'local';
        this.StorageKey.forEach((key) => {
          this.storageMethod.removeStorageItem(oppositeStorage, key);
        });

        this.storage = remember ? 'local' : 'session';

        const userName = res.first_name != undefined ? res.user_name : res.username;
        this.storageMethod.setStorageItem(this.storage, 'access_token', res.access);
        this.storageMethod.setStorageItem(this.storage, 'refresh_token', res.refresh);
        this.storageMethod.setStorageItem(
          this.storage,
          'is_profile_complete',
          res.is_profile_complete,
        );
        this.storageMethod.setStorageItem(this.storage, 'user_name', userName);
        this.storageMethod.setStorageItem(
          this.storage,
          'professional_title',
          res.professional_title ?? '',
        );
        this.storageMethod.setStorageItem(
          this.storage,
          'profile_photo',
          res.profile_photo ?? '',
        );
        // Boolean → string para el storage; el getter compara contra 'true'.
        // Si el backend no lo mandó (versión vieja del backend), default a
        // false — seguro porque deny by default.
        this.storageMethod.setStorageItem(
          this.storage,
          'is_staff',
          res.is_staff ? 'true' : 'false',
        );
        // Tipo de cuenta — viene del JWT payload. Si el backend no lo
        // manda (sesión cacheada de versión vieja), default `professional`
        // para back-compat.
        this.storageMethod.setStorageItem(
          this.storage,
          'account_type',
          res.account_type === 'company' ? 'company' : 'professional',
        );
        sessionStorage.setItem('user_email', res.email);
        this.isLoggedInSubject.next(true);
        this.isAdminSubject.next(this.getIsAdmin());
        this.accountTypeSubject.next(this.getAccountType());
        this.updateProfileStatus();
      }),
    );
  }

  logout(): void {
    sessionStorage.clear();
    this.StorageKey.forEach((key) => {
      localStorage.removeItem(key);
    });
    this.isLoggedInSubject.next(false);
    this.isAdminSubject.next(false);
    this.accountTypeSubject.next('professional');
    this.updateProfileStatus();
  }

  refreshToken(): Observable<any> {
    const refresh = this.storageMethod.getStorageItem(this.storage, 'refresh_token');
    if (!refresh) {
      return throwError(() => new Error('Refresh token missing'));
    }
    return this.http.post(`${environment.apiUrl}/token/refresh/`, { refresh }).pipe(
      tap((res: any) => {
        this.storageMethod.setStorageItem(this.storage, 'access_token', res.access);
        this.isLoggedInSubject.next(true);
      }),
    );
  }

  requestPasswordReset(email: string): Observable<any> {
    return this.http.post(`${environment.apiUrl}/users/password-reset/request/`, { email });
  }

  verifyPasswordReset(data: {
    email: string;
    code: string;
    new_password: string;
  }): Observable<any> {
    return this.http.post(`${environment.apiUrl}/users/password-reset/verify/`, data);
  }

  /** POST /users/me/change-password/ — el user logueado cambia su pass.
   *  El backend valida `current_password` y exige `new_password === confirm`. */
  changePassword(data: {
    current_password: string;
    new_password: string;
    confirm_password: string;
  }): Observable<any> {
    return this.http.post(`${environment.apiUrl}/users/me/change-password/`, data);
  }
}

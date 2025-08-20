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

@Injectable({
  providedIn: 'root'
})
export class AuthService {
  private apiUrl = 'http://localhost:8000/api/users/register/';
  private isLoggedInSubject = new BehaviorSubject<boolean>(!!this.getToken());
  isLoggedIn$ = this.isLoggedInSubject.asObservable();
  private isProfileCompleteSubject = new BehaviorSubject<boolean>(this.getProfileStatus());
  isProfileComplete$ = this.isProfileCompleteSubject.asObservable();
  StorageKey = [
    'access_token', 
    'refresh_token', 
    'storage', 'user', 
    'user_id', 'user_name', 
    'is_profile_complete', 
    'manual_profile_draft'
  ];
  storage: 'session' | 'local' = 'session';

  constructor(private http: HttpClient, private storageMethod: StorageMethodComponent) { }

  getToken(): string | null {
    if (localStorage.getItem("storage") === 'true') {
      return localStorage.getItem('access_token');
    } else {
      return sessionStorage.getItem('access_token');
    }
  }

  private getProfileStatus(): boolean {
    if (localStorage.getItem("storage") === 'true') {
      return localStorage.getItem('is_profile_complete') === 'true';
    } else {
      return sessionStorage.getItem('is_profile_complete') === 'true';
    }
  }

  updateProfileStatus(): void {
    const status = this.getProfileStatus()
    this.isProfileCompleteSubject.next(status);
  }

  syncAuthStatus(): void {
    this.isLoggedInSubject.next(!!this.getToken());
  }

  isAuthenticated(): boolean {
    return !!this.getToken();
  }

  register(data: RegisterData): Observable<any> {
    return this.http.post(this.apiUrl, data);
  }

  login(credentials: { username: string, password: string }) {
    return this.http.post(`${environment.apiUrl}/token/login/`, credentials).pipe(
      tap((res: any) => {
        const userName = res.first_name != undefined ? res.user_name : res.username;
        this.storage = localStorage.getItem('storage') === 'true' ? 'local' : 'session';
        this.storageMethod.setStorageItem(this.storage, 'access_token', res.access)
        this.storageMethod.setStorageItem(this.storage, 'refresh_token', res.refresh)
        this.storageMethod.setStorageItem(this.storage, 'is_profile_complete', res.is_profile_complete)
        this.storageMethod.setStorageItem(this.storage, 'user_name', userName);
        sessionStorage.setItem('user_email', res.email);
        this.isLoggedInSubject.next(true);
        this.updateProfileStatus();
      })
    );
  }

  logout(): void {
    sessionStorage.clear();
    this.StorageKey.forEach(key => {
      localStorage.removeItem(key);
    });
    this.isLoggedInSubject.next(false);
    this.updateProfileStatus();
  }

  refreshToken(): Observable<any> {
    const refresh = this.storageMethod.getStorageItem(this.storage, 'refresh_token')
    if(!refresh) {
      return throwError(() => new Error('Refresh token missing'));
    }
    return this.http.post(`${environment.apiUrl}/token/refresh/`, { refresh }).pipe(
      tap((res: any) => {
        this.storageMethod.setStorageItem(this.storage, 'access_token', res.access)
        this.isLoggedInSubject.next(true);
      })
    )
  }
}
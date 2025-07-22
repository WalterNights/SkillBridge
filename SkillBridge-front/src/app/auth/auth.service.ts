import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { tap, BehaviorSubject, Observable } from 'rxjs';
import { environment } from '../../environment/environment';

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

  constructor(private http: HttpClient) {}

  getToken(): string | null {
    return sessionStorage.getItem('access_token');
  }

  private getProfileStatus(): boolean {
    return sessionStorage.getItem('is_profile_complete') === 'true';
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

  login(credentials: {username: string, password: string}) {
    return this.http.post(`${environment.apiUrl}/token/login/`, credentials).pipe(
      tap((res: any) => {
        sessionStorage.setItem('access_token', res.access);
        sessionStorage.setItem('refresh_token', res.refresh_token);
        sessionStorage.setItem('is_profile_complete', res.is_profile_complete);
        sessionStorage.setItem('user_name', res.username);
        this.isLoggedInSubject.next(true);
        this.updateProfileStatus();
      })
    );
  }

  logout(): void {
    sessionStorage.clear();
    this.isLoggedInSubject.next(false);
    this.updateProfileStatus();
  }

  refreshToken(): Observable<any> {
    const refresh = sessionStorage.getItem('refresh_token');
    return this.http.post(`${environment.apiUrl}/token/refresh/`, { refresh }).pipe(
      tap((res: any) => {
        sessionStorage.setItem('access_token', res.access);
        this.isLoggedInSubject.next(true);
      })
    )
  }
}
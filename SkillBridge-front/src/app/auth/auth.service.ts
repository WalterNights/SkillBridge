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
  private isLoggedInSubject = new BehaviorSubject<boolean>(this.hasToken());
  isLoggedIn$ = this.isLoggedInSubject.asObservable();
  constructor(private http: HttpClient) {}
  private hasToken(): boolean {
    return !!sessionStorage.getItem('access_token');
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
        this.isLoggedInSubject.next(true);
      })
    );
  }
  logout(){
    sessionStorage.clear();
    this.isLoggedInSubject.next(false);
  }
  refreshToken() {
    const refresh = sessionStorage.getItem('refresh_token');
    return this.http.post(`${environment.apiUrl}/token/refresh/`, { refresh }).pipe(
      tap((res: any) => {
        sessionStorage.setItem('access_token', res.access);
        this.isLoggedInSubject.next(true);
      })
    )
  }
}
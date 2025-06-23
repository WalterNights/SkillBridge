import { tap } from 'rxjs';
import { Observable } from 'rxjs';
import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
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
  constructor(private http: HttpClient) {}
  register(data: RegisterData): Observable<any> {
    return this.http.post(this.apiUrl, data);
  }
  login(credentials: {username: string, password: string}) {
    return this.http.post(`${environment.apiUrl}/token/login/`, credentials).pipe(
      tap((res: any) => {
        sessionStorage.setItem('access_token', res.access);
        sessionStorage.setItem('refresh_token', res.refresh_token);
        sessionStorage.setItem('is_profile_complete', res.is_profile_complete);
      })
    );
  }
  logout(){
    sessionStorage.clear();
  }
  refreshToken() {
    const refresh = sessionStorage.getItem('refresh_token');
    return this.http.post(`${environment.apiUrl}/token/refresh/`, { refresh }).pipe(
      tap((res: any) => {
        sessionStorage.setItem('access_token', res.access);
      })
    )
  }
}

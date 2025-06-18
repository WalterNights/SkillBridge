import { Observable } from 'rxjs';
import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';

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
}

import { Router } from '@angular/router';
import { Injectable } from '@angular/core';
import { Observable, catchError, throwError } from 'rxjs';
import { HttpInterceptor, HttpRequest, HttpHandler, HttpEvent, HttpErrorResponse } from '@angular/common/http';

import { StorageMethodComponent } from '../shared/storage-method/storage-method';

@Injectable({
  providedIn: 'root'
})
export class TokenInterceptorService implements HttpInterceptor {
  storage: 'session' | 'local' = 'session';

  constructor(private router: Router, private storageMethod: StorageMethodComponent) {}

  intercept(req: HttpRequest<any>, next: HttpHandler): Observable<HttpEvent<any>> {

    let authReq = req;

    if (!req.url.includes('/register') && !req.url.includes('/token')) {
      this.storage = localStorage.getItem('storage') === 'true' ? 'local' : 'session'; // Reduce the if and else login in one line
      const token = this.storageMethod.getStorageItem(this.storage, 'access_token');
      if (token) {
        authReq = req.clone({
          setHeaders: {
            Authorization: `Bearer ${token}`
          }
        });
      }
    }

    return next.handle(authReq).pipe(
      catchError((error: HttpErrorResponse) => {
        if (error.status === 401) {
          sessionStorage.clear();
          this.router.navigate(['auth/login']);
        }
        return throwError(() => error);
      })
    );
  }
}
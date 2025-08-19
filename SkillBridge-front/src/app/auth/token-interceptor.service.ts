import { Router } from '@angular/router';
import { Injectable } from '@angular/core';
import { AuthService } from './auth.service';
import { Observable, catchError, switchMap, throwError } from 'rxjs';
import { StorageMethodComponent } from '../shared/storage-method/storage-method';
import { HttpInterceptor, HttpRequest, HttpHandler, HttpEvent, HttpErrorResponse } from '@angular/common/http';


@Injectable({
  providedIn: 'root'
})

export class TokenInterceptorService implements HttpInterceptor {
  storage: 'session' | 'local' = 'session';

  constructor(
    private router: Router,
    private authService: AuthService, 
    private storageMethod: StorageMethodComponent
  ) {}

  intercept(req: HttpRequest<any>, next: HttpHandler): Observable<HttpEvent<any>> {
    this.storage = localStorage.getItem('storage') === 'true' ? 'local' : 'session';
    let token = this.storageMethod.getStorageItem(this.storage, 'access_token');
    let authReq = req;

    if (!req.url.includes('/register') && !req.url.includes('/token')) {
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
          // Try to refresh token
          return this.authService.refreshToken().pipe(
            switchMap(() => {
              token = this.authService.getToken();
              if (token) {
                const newReq = req.clone({
                  setHeaders: {
                    Authorization: `Bearer ${token}`
                  }
                });
                // Retry the request
                return next.handle(newReq);
              }
              this.authService.logout();
              this.router.navigate(['auth/login'])
              return throwError(() => error);
            }),
            catchError(() => {
              this.authService.logout();
              this.router.navigate(['auth/login'])
              return throwError(() => error);
            })
          );
        }
        return throwError(() => error);
      })
    );
  }
}
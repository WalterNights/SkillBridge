import { Router } from '@angular/router';
import { Injectable } from '@angular/core';
import { AuthService } from './auth.service';
import { Observable, catchError, switchMap, throwError } from 'rxjs';
import { StorageMethodComponent } from '../shared/storage-method/storage-method';
import {
  HttpInterceptor,
  HttpRequest,
  HttpHandler,
  HttpEvent,
  HttpErrorResponse,
} from '@angular/common/http';

@Injectable({
  providedIn: 'root',
})
export class TokenInterceptorService implements HttpInterceptor {
  storage: 'session' | 'local' = 'session';

  constructor(
    private router: Router,
    private authService: AuthService,
    private storageMethod: StorageMethodComponent,
  ) {}

  intercept(req: HttpRequest<any>, next: HttpHandler): Observable<HttpEvent<any>> {
    this.storage = localStorage.getItem('storage') === 'true' ? 'local' : 'session';
    let token = this.storageMethod.getStorageItem(this.storage, 'access_token');
    let authReq = req;

    if (!req.url.includes('/register') && !req.url.includes('/token')) {
      if (token) {
        authReq = req.clone({
          setHeaders: {
            Authorization: `Bearer ${token}`,
          },
        });
      }
    }

    return next.handle(authReq).pipe(
      catchError((error: HttpErrorResponse) => {
        // Solo intentamos refresh para 401 de requests autenticadas.
        // Si el 401 viene de /token/refresh o /token/login mismo, NO
        // re-llamamos a refresh — eso era un loop infinito cuando el
        // refresh-token estaba expirado/inválido (cada 401 disparaba
        // otro refresh que también daba 401).
        //
        // Tampoco refreshamos si no hay refresh-token guardado, ni si
        // la request original era una de las públicas (login/register).
        const isAuthEndpoint = req.url.includes('/token') || req.url.includes('/register');
        const hasRefresh = !!this.storageMethod.getStorageItem(this.storage, 'refresh_token');
        if (error.status !== 401 || isAuthEndpoint || !hasRefresh) {
          // Si era 401 sobre una request autenticada pero no hay refresh
          // (sesión perdida) — logout silencioso para evitar requests
          // colgadas con tokens expirados. No navegamos: las rutas
          // públicas no se bloquean.
          if (error.status === 401 && !isAuthEndpoint && !hasRefresh) {
            this.authService.logout();
          }
          return throwError(() => error);
        }

        // Try to refresh token
        return this.authService.refreshToken().pipe(
          switchMap(() => {
            token = this.authService.getToken();
            if (token) {
              const newReq = req.clone({
                setHeaders: {
                  Authorization: `Bearer ${token}`,
                },
              });
              return next.handle(newReq);
            }
            this.authService.logout();
            this.router.navigate(['auth/login']);
            return throwError(() => error);
          }),
          catchError(() => {
            this.authService.logout();
            this.router.navigate(['auth/login']);
            return throwError(() => error);
          }),
        );
      }),
    );
  }
}

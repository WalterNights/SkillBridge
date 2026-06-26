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
          // Sesión perdida sobre un endpoint autenticado: kick al login
          // con hard reload. El soft navigate dejaba colgado el shell
          // con datos viejos si había varias requests en flight.
          if (error.status === 401 && !isAuthEndpoint && !hasRefresh) {
            this.kickToLogin();
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
            this.kickToLogin();
            return throwError(() => error);
          }),
          catchError(() => {
            this.kickToLogin();
            return throwError(() => error);
          }),
        );
      }),
    );
  }

  /** Cierra sesión y fuerza navegación dura al login.
   *
   *  Por qué hard reload (window.location en vez de router.navigate):
   *  cuando el refresh falla puede haber 5-10 requests in-flight que
   *  fallan en paralelo y el SPA queda con state inconsistente
   *  (componentes pintando datos parciales, otros disparando más
   *  requests con token muerto). El reload limpia todo el árbol de
   *  componentes y observables, asegurando estado clean en login.
   *
   *  Además, el navigate previo era `['auth/login']` SIN slash inicial,
   *  lo cual Angular interpreta como ruta RELATIVA al activated route
   *  actual — desde `/dashboard` resolvía a `/dashboard/auth/login`,
   *  caía en el wildcard `**` y redirigía a la landing dejando al user
   *  confundido con sesión muerta. Hard reload elimina esta clase de
   *  bugs.
   */
  private kickToLogin(): void {
    this.authService.logout();
    if (typeof window !== 'undefined') {
      window.location.assign('/auth/login');
    } else {
      this.router.navigate(['/auth/login']);
    }
  }
}

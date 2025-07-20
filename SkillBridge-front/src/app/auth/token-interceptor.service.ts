import { Router } from '@angular/router';
import { Injectable } from '@angular/core';
import { Observable, catchError, throwError } from 'rxjs';
import { HttpInterceptor, HttpRequest, HttpHandler, HttpEvent, HttpErrorResponse } from '@angular/common/http';

@Injectable({
  providedIn: 'root'
})
export class TokenInterceptorService implements HttpInterceptor {

  constructor(private router: Router) {}

  intercept(req: HttpRequest<any>, next: HttpHandler): Observable<HttpEvent<any>> {

    let authReq = req;

    if (!req.url.includes('/register') && !req.url.includes('/token')) {
      const token = sessionStorage.getItem('access_token');
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
import { routes } from './app.routes';
import { provideRouter, withInMemoryScrolling } from '@angular/router';
import { TokenInterceptorService } from './auth/token-interceptor.service';
import { ApplicationConfig, provideZoneChangeDetection } from '@angular/core';
import { HTTP_INTERCEPTORS, provideHttpClient, withInterceptorsFromDi } from '@angular/common/http';
import { provideAnimations } from '@angular/platform-browser/animations';

export const appConfig: ApplicationConfig = {
  providers: [
    provideZoneChangeDetection({ eventCoalescing: true }),
    provideRouter(
      routes,
      // anchorScrolling: hace que `routerLink="/x" fragment="y"` haga
      //   scroll a <... id="y"> después de cargar la ruta. Sin esto,
      //   los enlaces a anclas dentro de otras páginas no funcionan.
      // scrollPositionRestoration: al navegar back, restaura la posición
      //   scrolleada previa en vez de quedar en top.
      withInMemoryScrolling({
        anchorScrolling: 'enabled',
        scrollPositionRestoration: 'enabled',
      }),
    ),
    provideHttpClient(withInterceptorsFromDi()),
    provideAnimations(), // Enable animations globally
    {
      provide: HTTP_INTERCEPTORS,
      useClass: TokenInterceptorService,
      multi: true,
    },
  ],
};

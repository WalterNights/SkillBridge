import { routes } from './app.routes';
import { NavigationError, provideRouter, withInMemoryScrolling, withNavigationErrorHandler } from '@angular/router';
import { TokenInterceptorService } from './auth/token-interceptor.service';
import { ApplicationConfig, provideZoneChangeDetection } from '@angular/core';
import { HTTP_INTERCEPTORS, provideHttpClient, withInterceptorsFromDi } from '@angular/common/http';
import { provideAnimations } from '@angular/platform-browser/animations';

// Tras un deploy, un browser con el index.html viejo cacheado sigue pidiendo
// chunks hasheados que el build nuevo ya borró → el import() dinámico de la
// ruta lazy tira "Failed to fetch dynamically imported module" y la navegación
// queda muerta. Detectamos ese caso y forzamos un reload completo: como el
// index.html ahora se sirve con no-cache, el reload trae el build actual y la
// ruta carga bien. Guard con sessionStorage para no entrar en loop si el fallo
// fuese real (chunk genuinamente faltante, red caída): solo un reload cada 10s.
const CHUNK_ERROR_RE = /(Failed to fetch dynamically imported module|error loading dynamically imported module|Importing a module script failed|ChunkLoadError)/i;

function reloadOnChunkLoadError(nav: NavigationError): void {
  const message = String(nav.error?.message ?? nav.error ?? '');
  if (!CHUNK_ERROR_RE.test(message)) return;

  const now = Date.now();
  const last = Number(sessionStorage.getItem('chunkReloadAt') ?? '0');
  if (now - last < 10_000) return; // ya recargamos hace poco; evitar loop

  sessionStorage.setItem('chunkReloadAt', String(now));
  location.reload();
}

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
      withNavigationErrorHandler(reloadOnChunkLoadError),
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

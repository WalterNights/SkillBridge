import { Routes } from '@angular/router';
import { AutoGuard } from './auth/auto.guard';
import { AdminGuard } from './auth/admin.guard';
import { CompanyGuard } from './auth/company.guard';
import { authMatchGuard } from './auth/auth-match.guard';

/**
 * SkilTak IA (post-refactor).
 *
 *   PUBLIC (no auth):
 *     /                      Landing
 *     /auth/*                register, login, password reset
 *
 *   AUTHENTICATED STANDALONE (AutoGuard, no shell):
 *     /profile               Onboarding wizard (first-time — runs once)
 *     /cv                    ATS CV viewer (print-preview style)
 *
 *   AUTHENTICATED IN SHELL (AutoGuard + AppShell):
 *     /dashboard             role-aware home (user → offers, admin → panel)
 *     /jobs/:id              Job offer detail
 *     /me                    Mi perfil — view + update (post-onboarding)
 *     /settings              Settings
 *
 *   ADMIN IN SHELL (AutoGuard + AppShell + AdminGuard):
 *     /admin/users           User list
 *     /admin/stats           Platform stats (TODO)
 *
 * Legacy paths keep redirects so existing bookmarks/emails still work.
 */
export const routes: Routes = [
  // ===== Public =====
  {
    path: '',
    pathMatch: 'full',
    loadComponent: () => import('./home/home.component').then((m) => m.HomeComponent),
  },
  {
    path: 'auth',
    loadChildren: () => import('./auth/auth.module').then((m) => m.AuthModule),
  },

  // ===== SHELL para rutas PUBLIC-OR-AUTH (auth wraps en shell, unauth cae
  // al fallback público abajo). canMatch deja al router probar la siguiente
  // ruta si el user no está autenticado, en vez de bouncear a login. =====
  {
    path: '',
    canMatch: [authMatchGuard],
    loadComponent: () => import('./shell/app-shell.component').then((m) => m.AppShellComponent),
    children: [
      {
        path: 'recursos',
        loadComponent: () =>
          import('./public/recursos/recursos.component').then((m) => m.RecursosComponent),
      },
      {
        path: 'recursos/:slug',
        loadComponent: () =>
          import('./public/articulo/articulo.component').then((m) => m.ArticuloComponent),
      },
      {
        path: 'blog',
        loadComponent: () => import('./public/blog/blog.component').then((m) => m.BlogComponent),
      },
    ],
  },

  // Public marketing pages — no auth required. Comparten <app-public-nav>
  // + <app-public-footer> internamente.
  {
    path: 'como-funciona',
    loadComponent: () =>
      import('./public/como-funciona/como-funciona.component').then((m) => m.ComoFuncionaComponent),
  },
  {
    path: 'faq',
    loadComponent: () => import('./public/faq/faq.component').then((m) => m.FaqComponent),
  },
  // Fallback público de /recursos y /blog. Los componentes detectan auth
  // state y skip PublicNav/PublicFooter cuando están dentro del shell.
  {
    path: 'recursos',
    loadComponent: () =>
      import('./public/recursos/recursos.component').then((m) => m.RecursosComponent),
  },
  {
    path: 'recursos/:slug',
    loadComponent: () =>
      import('./public/articulo/articulo.component').then((m) => m.ArticuloComponent),
  },
  {
    path: 'blog',
    loadComponent: () => import('./public/blog/blog.component').then((m) => m.BlogComponent),
  },
  // Documentos legales — privacidad, terminos, cookies. Comparten un único
  // componente que hace lookup por slug en legal-data.ts. URLs públicas y
  // estables porque las usan terceros (LinkedIn Developers pide privacy URL).
  {
    path: 'legal/:slug',
    loadComponent: () =>
      import('./public/legal/legal.component').then((m) => m.LegalComponent),
  },

  // ===== Authenticated standalone (no shell) =====
  // /profile sigue afuera porque es el wizard de onboarding — no
  // queremos sidebar visible mientras el usuario completa los pasos.
  {
    path: 'profile',
    canActivate: [AutoGuard],
    loadComponent: () => import('./auth/profile/profile.component').then((m) => m.ProfileComponent),
  },

  // ===== Legacy redirects (must precede shell parent to match first) =====
  { path: 'manual-profile', redirectTo: 'profile', pathMatch: 'full' },
  { path: 'results', redirectTo: 'dashboard', pathMatch: 'full' },
  { path: 'ats-cv', redirectTo: 'cv', pathMatch: 'full' },
  { path: 'dashboard/settings', redirectTo: 'settings', pathMatch: 'full' },

  // ===== Authenticated routes wrapped in AppShell =====
  {
    path: '',
    canActivate: [AutoGuard],
    loadComponent: () => import('./shell/app-shell.component').then((m) => m.AppShellComponent),
    children: [
      {
        path: 'dashboard',
        loadComponent: () => import('./results/results.component').then((m) => m.ResultsComponent),
      },
      {
        path: 'jobs/:id',
        loadComponent: () =>
          import('./job-detail/job-detail.component').then((m) => m.JobDetailComponent),
      },
      {
        path: 'me',
        loadComponent: () =>
          import('./account/my-profile/my-profile.component').then((m) => m.MyProfileComponent),
      },
      {
        path: 'cv',
        loadComponent: () => import('./ats-cv/ats-cv.component').then((m) => m.AtsCvComponent),
      },
      {
        path: 'applications',
        loadComponent: () =>
          import('./applications/applications.component').then((m) => m.ApplicationsComponent),
      },
      {
        path: 'ignored',
        loadComponent: () =>
          import('./ignored-offers/ignored-offers.component').then(
            (m) => m.IgnoredOffersComponent,
          ),
      },
      {
        path: 'settings',
        loadComponent: () =>
          import('./dashboard/settings/settings.component').then((m) => m.SettingsComponent),
      },
      {
        // Inbox del profesional — "empresas interesadas en mí". El
        // backend ya rechaza con 403 si la cuenta es company, pero
        // mostramos un mensaje claro en el componente.
        path: 'inbox',
        loadComponent: () =>
          import('./inbox/company-interests-inbox.component').then(
            (m) => m.CompanyInterestsInboxComponent,
          ),
      },
      {
        path: 'admin',
        canActivate: [AdminGuard],
        children: [
          { path: '', redirectTo: 'users', pathMatch: 'full' },
          {
            path: 'users',
            loadComponent: () =>
              import('./admin/admin-users.component').then((m) => m.AdminUsersComponent),
          },
          {
            path: 'stats',
            loadComponent: () =>
              import('./admin/admin-stats.component').then((m) => m.AdminStatsComponent),
          },
          {
            path: 'faqs',
            loadComponent: () =>
              import('./admin/admin-faqs.component').then((m) => m.AdminFaqsComponent),
          },
          {
            path: 'feature-flags',
            loadComponent: () =>
              import('./admin/admin-feature-flags.component').then(
                (m) => m.AdminFeatureFlagsComponent,
              ),
          },
        ],
      },
      // ════════════════════════════════════════════════════════════
      // Lado empresa del marketplace — gated por CompanyGuard. Una
      // cuenta professional intentando /company/* es redirigida a
      // /dashboard (espejo del comportamiento de AdminGuard).
      // ════════════════════════════════════════════════════════════
      {
        path: 'company',
        canActivate: [CompanyGuard],
        children: [
          { path: '', redirectTo: 'dashboard', pathMatch: 'full' },
          {
            path: 'dashboard',
            loadComponent: () =>
              import('./company/company-dashboard.component').then(
                (m) => m.CompanyDashboardComponent,
              ),
          },
          {
            path: 'me',
            loadComponent: () =>
              import('./company/company-me.component').then((m) => m.CompanyMeComponent),
          },
          {
            path: 'profiles/:id',
            loadComponent: () =>
              import('./company/company-profile-detail.component').then(
                (m) => m.CompanyProfileDetailComponent,
              ),
          },
        ],
      },
    ],
  },

  // ===== 404 → landing. AutoGuard handles redirecting to login when needed. =====
  { path: '**', redirectTo: '' },
];

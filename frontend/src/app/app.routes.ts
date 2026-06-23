import { Routes } from '@angular/router';
import { AutoGuard } from './auth/auto.guard';
import { AdminGuard } from './auth/admin.guard';

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
  // Public marketing pages — no auth required. Comparten <app-public-nav>
  // + <app-public-footer> internamente.
  {
    path: 'como-funciona',
    loadComponent: () =>
      import('./public/como-funciona/como-funciona.component').then((m) => m.ComoFuncionaComponent),
  },
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
        path: 'settings',
        loadComponent: () =>
          import('./dashboard/settings/settings.component').then((m) => m.SettingsComponent),
      },
      {
        path: 'admin',
        canActivate: [AdminGuard],
        children: [
          { path: '', redirectTo: 'users', pathMatch: 'full' },
          {
            path: 'users',
            loadComponent: () =>
              import('./dashboard/dashboard.component').then((m) => m.DashboardComponent),
          },
        ],
      },
    ],
  },

  // ===== 404 → landing. AutoGuard handles redirecting to login when needed. =====
  { path: '**', redirectTo: '' },
];

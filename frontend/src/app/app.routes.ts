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
 *   AUTHENTICATED (AutoGuard, shared AppShell):
 *     /dashboard             role-aware home (user → offers, admin → panel)
 *     /jobs/:id              Job offer detail
 *     /profile               Profile editor (replaces /profile + /manual-profile)
 *     /cv                    ATS CV viewer
 *     /settings              Settings
 *
 *   ADMIN (AutoGuard + AdminGuard):
 *     /admin/users           User list
 *     /admin/stats           Platform stats
 *
 * Legacy paths keep redirects so existing bookmarks/emails still work.
 */
export const routes: Routes = [
  // Public
  {
    path: '',
    loadComponent: () => import('./home/home.component').then((m) => m.HomeComponent),
  },
  {
    path: 'auth',
    loadChildren: () => import('./auth/auth.module').then((m) => m.AuthModule),
  },

  // Authenticated app
  {
    path: 'dashboard',
    canActivate: [AutoGuard],
    loadComponent: () => import('./results/results.component').then((m) => m.ResultsComponent),
  },
  {
    path: 'jobs/:id',
    canActivate: [AutoGuard],
    loadComponent: () =>
      import('./job-detail/job-detail.component').then((m) => m.JobDetailComponent),
  },
  {
    path: 'profile',
    canActivate: [AutoGuard],
    loadComponent: () => import('./auth/profile/profile.component').then((m) => m.ProfileComponent),
  },
  {
    path: 'cv',
    canActivate: [AutoGuard],
    loadComponent: () => import('./ats-cv/ats-cv.component').then((m) => m.AtsCvComponent),
  },
  {
    path: 'settings',
    canActivate: [AutoGuard],
    loadComponent: () =>
      import('./dashboard/settings/settings.component').then((m) => m.SettingsComponent),
  },

  // Admin
  {
    path: 'admin',
    canActivate: [AutoGuard, AdminGuard],
    children: [
      { path: '', redirectTo: 'users', pathMatch: 'full' },
      {
        path: 'users',
        loadComponent: () =>
          import('./dashboard/dashboard.component').then((m) => m.DashboardComponent),
      },
    ],
  },

  // Redirects from legacy paths. Old bookmarks/emails keep working
  // until we confirm nothing external still references them.
  { path: 'manual-profile', redirectTo: 'profile', pathMatch: 'full' },
  { path: 'results', redirectTo: 'dashboard', pathMatch: 'full' },
  { path: 'ats-cv', redirectTo: 'cv', pathMatch: 'full' },
  { path: 'dashboard/settings', redirectTo: 'settings', pathMatch: 'full' },

  // 404 → landing. AutoGuard handles redirecting to login when needed.
  { path: '**', redirectTo: '' },
];

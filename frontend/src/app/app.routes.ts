import { Routes } from '@angular/router';
import { AutoGuard } from './auth/auto.guard';

export const routes: Routes = [
  { path: '', loadComponent: () => import('./home/home.component').then(m => m.HomeComponent) },
  { path: 'auth', loadChildren: () => import('./auth/auth.module').then(m => m.AuthModule) },
  { path: 'manual-profile', canActivate: [AutoGuard], loadComponent: () => import('./auth/manual-profile/manual-profile.component').then(m => m.ManualProfileComponent) },
  { path: 'profile', canActivate: [AutoGuard], loadComponent: () => import('./auth/profile/profile.component').then(m => m.ProfileComponent) },
  { path: 'results', loadComponent: () => import('./results/results.component').then(m => m.ResultsComponent) },
  { path: 'ats-cv', loadComponent: () => import('./ats-cv/ats-cv.component').then(m => m.AtsCvComponent) },
  { path: 'jobs/:id', loadComponent: () => import('./job-detail/job-detail.component').then(m => m.JobDetailComponent) },
  {
    path: 'dashboard',
    children: [
      { path: '', loadComponent: () => import('./dashboard/dashboard.component').then(m => m.DashboardComponent) },
      { path: 'settings', loadComponent: () => import('./dashboard/settings/settings.component').then(m => m.SettingsComponent) },
    ]
  },
  { path: '**', redirectTo: 'auth/register' }
];

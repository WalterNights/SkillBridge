import { Routes } from '@angular/router';
import { AutoGuard } from './auth/auto.guard';

export const routes: Routes = [
  {path: '', loadComponent: () => import('./home/home.component').then(m => m.HomeComponent)},
  {path: 'auth', loadChildren: () => import('./auth/auth.module').then(m => m.AuthModule)},
  {path: 'profile', canActivate: [AutoGuard], loadComponent: () => import('./auth/profile/profile.component').then(m => m.ProfileComponent)},
  {path: 'results', loadComponent: () => import('./results/results.component').then(m => m.ResultsComponent)},
  {path: '**', redirectTo: 'auth/register'}
];
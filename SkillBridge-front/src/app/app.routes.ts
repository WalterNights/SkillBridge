import { Routes } from '@angular/router';

export const routes: Routes = [
  {path: 'auth', loadComponent: () => import('./auth/auth.module').then(m => m.AuthModule)},
  {path: '', redirectTo: 'auth/register', pathMatch: 'full'},
  {path: '**', redirectTo: 'auth/register'}
];
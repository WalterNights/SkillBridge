import { Routes } from '@angular/router';
import { AutoGuard } from './auth/auto.guard';

export const routes: Routes = [
  {path: 'auth', loadChildren: () => import('./auth/auth.module').then(m => m.AuthModule)},

  {path: '**', redirectTo: 'auth/register'},
  {path: '', redirectTo: 'auth/register', pathMatch: 'full'},
  {path: 'login', loadComponent: () => import('./auth/login/login.component').then(m => m.LoginComponent)},
  {path: 'profile', canActivate: [AutoGuard], loadComponent: () => import('./auth/profile/profile.component').then(m => m.ProfileComponent)}
];
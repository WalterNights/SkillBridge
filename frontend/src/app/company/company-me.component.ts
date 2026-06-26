import { CommonModule } from '@angular/common';
import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { Component, OnInit, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Title } from '@angular/platform-browser';

import { environment } from '../../environment/environment';
import { ToastService } from '../services/toast.service';

/** Shape de los campos editables del CompanyProfile. Espeja el backend
 *  `CompanyProfileSerializer`. */
interface CompanyMeData {
  legal_name: string;
  country: string;
  city: string;
  industry: string;
  website: string;
  size: string;
  short_description: string;
  responsible_name: string;
  responsible_role: string;
  responsible_email: string;
}

const COMPANY_SIZE_OPTIONS = [
  { value: '', label: '—' },
  { value: '1-10', label: '1-10 empleados' },
  { value: '11-50', label: '11-50 empleados' },
  { value: '51-200', label: '51-200 empleados' },
  { value: '201-500', label: '201-500 empleados' },
  { value: '501-1000', label: '501-1000 empleados' },
  { value: '1000+', label: 'Más de 1000 empleados' },
];

/**
 * Perfil editable de la empresa logueada (/company/me).
 *
 * GET inicial llena el form. Submit hace PATCH parcial. Mantiene el
 * estilo del Settings tab "Cuenta" para consistencia visual.
 */
@Component({
  selector: 'app-company-me',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './company-me.component.html',
  styleUrls: ['./company-me.component.scss'],
})
export class CompanyMeComponent implements OnInit {
  private http = inject(HttpClient);
  private toast = inject(ToastService);
  private titleService = inject(Title);

  isLoading = signal(true);
  isSaving = signal(false);
  errorMessage = signal('');

  form: CompanyMeData = {
    legal_name: '',
    country: '',
    city: '',
    industry: '',
    website: '',
    size: '',
    short_description: '',
    responsible_name: '',
    responsible_role: '',
    responsible_email: '',
  };

  readonly sizeOptions = COMPANY_SIZE_OPTIONS;

  constructor() {
    this.titleService.setTitle('SkilTak — Empresa · Perfil');
  }

  ngOnInit(): void {
    this.http
      .get<CompanyMeData>(`${environment.apiUrl}/companies/me/`)
      .subscribe({
        next: (data) => {
          // El backend devuelve más fields (user nested, timestamps);
          // copiamos solo los editables para mantener el form limpio.
          this.form = {
            legal_name: data.legal_name ?? '',
            country: data.country ?? '',
            city: data.city ?? '',
            industry: data.industry ?? '',
            website: data.website ?? '',
            size: data.size ?? '',
            short_description: data.short_description ?? '',
            responsible_name: data.responsible_name ?? '',
            responsible_role: data.responsible_role ?? '',
            responsible_email: data.responsible_email ?? '',
          };
          this.isLoading.set(false);
        },
        error: (err: HttpErrorResponse) => {
          this.errorMessage.set(
            err.status === 403
              ? 'Esta cuenta no es de tipo empresa.'
              : 'No pudimos cargar el perfil. Recargá la página.',
          );
          this.isLoading.set(false);
        },
      });
  }

  save(): void {
    if (!this.form.legal_name.trim()) {
      this.errorMessage.set('El nombre comercial es obligatorio.');
      return;
    }
    if (!this.form.responsible_email.trim()) {
      this.errorMessage.set('El email del responsable es obligatorio.');
      return;
    }

    this.errorMessage.set('');
    this.isSaving.set(true);
    this.http
      .patch<CompanyMeData>(`${environment.apiUrl}/companies/me/`, this.form)
      .subscribe({
        next: () => {
          this.isSaving.set(false);
          this.toast.success('Perfil de empresa actualizado.');
        },
        error: (err: HttpErrorResponse) => {
          this.isSaving.set(false);
          const body = err.error;
          if (body && typeof body === 'object') {
            const firstField = Object.keys(body)[0];
            const msg = Array.isArray(body[firstField])
              ? body[firstField][0]
              : body[firstField];
            this.errorMessage.set(`${firstField}: ${msg}`);
          } else {
            this.errorMessage.set('No pudimos guardar. Intenta de nuevo.');
          }
        },
      });
  }
}

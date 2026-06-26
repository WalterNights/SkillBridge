import { CommonModule } from '@angular/common';
import { Component, inject, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Title } from '@angular/platform-browser';
import { RouterLink } from '@angular/router';

import { environment } from '../../environment/environment';

/** Shape mínima del CompanyProfile que necesitamos en el home placeholder.
 *  El componente CompanyMeComponent maneja la versión completa. */
interface CompanyProfileLite {
  legal_name: string;
  responsible_name: string;
  industry: string;
  city: string;
  short_description: string;
}

/**
 * Home del lado empresa.
 *
 * FASE 1: placeholder con bienvenida + summary del perfil + CTA al
 * próximo feature (buscar profesionales, no disponible aún).
 *
 * FASE 2: aquí va el feed de "Profesionales que calzan con tu empresa"
 * — espejo del /dashboard del lado profesional.
 */
@Component({
  selector: 'app-company-dashboard',
  standalone: true,
  imports: [CommonModule, RouterLink],
  templateUrl: './company-dashboard.component.html',
  styleUrls: ['./company-dashboard.component.scss'],
})
export class CompanyDashboardComponent {
  private http = inject(HttpClient);

  company = signal<CompanyProfileLite | null>(null);

  constructor(title: Title) {
    title.setTitle('SkilTak — Empresa');
    // Cargar perfil para mostrar el saludo personalizado. Soft-fail —
    // el placeholder funciona aunque no haya datos.
    this.http
      .get<CompanyProfileLite>(`${environment.apiUrl}/companies/me/`)
      .subscribe({
        next: (data) => this.company.set(data),
        error: () => {
          /* swallow — placeholder muestra fallback */
        },
      });
  }
}

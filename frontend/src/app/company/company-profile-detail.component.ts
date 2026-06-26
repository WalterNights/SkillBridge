import { CommonModule } from '@angular/common';
import { HttpErrorResponse } from '@angular/common/http';
import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Title } from '@angular/platform-browser';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';

import { CompanyService, ProfileDetail } from '../services/company.service';
import { ToastService } from '../services/toast.service';

/**
 * Detalle completo del perfil profesional (vista empresa).
 *
 * El header trae foto, nombre, título y ciudad. El cuerpo presenta el
 * perfil en secciones (Resumen, Skills, Soft skills, Experiencia,
 * Educación, Idiomas, Links). El sidebar derecho expone acciones:
 *
 *   - Descargar CV (si el profesional subió uno)
 *   - Marcar interés → modal con mensaje opcional → POST al backend.
 *     Si ya marcaste, el botón cambia a "Ya marcaste interés" con la
 *     fecha + permite editar el mensaje.
 *
 * Privacidad: el backend NO entrega email/teléfono, así que esta vista
 * tampoco los muestra. El contacto real pasa por el inbox del
 * profesional (Fase 4).
 */
@Component({
  selector: 'app-company-profile-detail',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink],
  templateUrl: './company-profile-detail.component.html',
  styleUrls: ['./company-profile-detail.component.scss'],
})
export class CompanyProfileDetailComponent implements OnInit {
  private service = inject(CompanyService);
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private toast = inject(ToastService);
  private titleService = inject(Title);

  profile = signal<ProfileDetail | null>(null);
  isLoading = signal(true);
  notFound = signal(false);

  /** Modal de "marcar interés" — abre desde el botón principal. */
  isInterestModalOpen = signal(false);
  interestMessage = '';
  isSubmittingInterest = signal(false);

  /** Descarga del CV. Booleano simple para mostrar spinner. */
  isDownloading = signal(false);

  /** Skills parseadas para render como pills. El backend devuelve text
   *  comma-separated; lo splittean en computed para evitar parsing
   *  repetido en el template. */
  skillPills = computed<string[]>(() => {
    const p = this.profile();
    return (p?.skills || '')
      .split(',')
      .map((s) => s.trim())
      .filter(Boolean);
  });

  softSkillPills = computed<string[]>(() => {
    const p = this.profile();
    return (p?.soft_skills || '')
      .split(',')
      .map((s) => s.trim())
      .filter(Boolean);
  });

  hasMarkedInterest = computed<boolean>(() => {
    return this.profile()?.interest_status !== null;
  });

  constructor() {
    this.titleService.setTitle('SkilTak — Perfil profesional');
  }

  ngOnInit(): void {
    const idParam = this.route.snapshot.paramMap.get('id');
    const profileId = idParam ? parseInt(idParam, 10) : NaN;
    if (Number.isNaN(profileId)) {
      this.notFound.set(true);
      this.isLoading.set(false);
      return;
    }

    this.service.getProfileDetail(profileId).subscribe({
      next: (data) => {
        this.profile.set(data);
        this.isLoading.set(false);
      },
      error: (err: HttpErrorResponse) => {
        this.isLoading.set(false);
        if (err.status === 404) {
          this.notFound.set(true);
        } else if (err.status === 403) {
          this.toast.error('No tienes permisos para ver este perfil.');
          this.router.navigate(['/company/dashboard']);
        } else {
          this.toast.error('No pudimos cargar el perfil. Intentá de nuevo.');
        }
      },
    });
  }

  initials(p: ProfileDetail | null): string {
    if (!p) return '?';
    return ((p.first_name || '?').charAt(0) + (p.last_name || '').charAt(0)).toUpperCase();
  }

  // ─── Interest flow ────────────────────────────────────────────────

  openInterestModal(): void {
    this.interestMessage = '';
    this.isInterestModalOpen.set(true);
  }

  closeInterestModal(): void {
    if (this.isSubmittingInterest()) return;
    this.isInterestModalOpen.set(false);
  }

  submitInterest(): void {
    const p = this.profile();
    if (!p) return;

    this.isSubmittingInterest.set(true);
    this.service.markInterest(p.id, this.interestMessage.trim()).subscribe({
      next: (res) => {
        this.isSubmittingInterest.set(false);
        this.isInterestModalOpen.set(false);
        // Actualizamos el signal in-place para reflejar el nuevo estado
        // sin re-fetch.
        this.profile.set({
          ...p,
          interest_status: res.status,
          interest_marked_at: res.created_at,
        });
        this.toast.success(
          this.hasMarkedInterest()
            ? 'Mensaje actualizado.'
            : 'Interés marcado. El profesional recibió tu notificación.',
        );
      },
      error: (err: HttpErrorResponse) => {
        this.isSubmittingInterest.set(false);
        if (err.status === 403) {
          this.toast.error(
            'Has marcado interés demasiadas veces. Esperá una hora antes de seguir.',
          );
        } else {
          this.toast.error('No pudimos guardar tu interés. Intentá de nuevo.');
        }
      },
    });
  }

  // ─── Resume download ──────────────────────────────────────────────

  downloadResume(): void {
    const p = this.profile();
    if (!p || !p.has_resume) return;

    this.isDownloading.set(true);
    this.service.downloadResume(p.id).subscribe({
      next: (blob) => {
        this.isDownloading.set(false);
        // Forzar la descarga via object URL — el browser respeta el
        // filename del Content-Disposition del backend.
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `${p.first_name}_${p.last_name}_CV.pdf`;
        a.click();
        URL.revokeObjectURL(url);
      },
      error: () => {
        this.isDownloading.set(false);
        this.toast.error('No pudimos descargar el CV.');
      },
    });
  }
}

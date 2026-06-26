import { CommonModule } from '@angular/common';
import { HttpErrorResponse } from '@angular/common/http';
import { Component, OnInit, inject, signal } from '@angular/core';
import { Title } from '@angular/platform-browser';

import {
  FeatureFlagsService,
  SystemSetting,
} from '../services/feature-flags.service';
import { ToastService } from '../services/toast.service';

/**
 * Panel admin /admin/feature-flags — listar y togglear flags runtime.
 *
 * Los flags se crean en data migrations del backend (NO desde la UI)
 * para evitar typos que dejen flags inalcanzables desde el código que
 * los consume. Acá solo se ve `value_bool` (toggle) y la descripción.
 *
 * Doble-gating: el backend valida is_staff (403 si no); el frontend
 * usa AdminGuard del router como UX-gate.
 */
@Component({
  selector: 'app-admin-feature-flags',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './admin-feature-flags.component.html',
  styleUrls: ['./admin-feature-flags.component.scss'],
})
export class AdminFeatureFlagsComponent implements OnInit {
  private flagsService = inject(FeatureFlagsService);
  private toast = inject(ToastService);

  flags = signal<SystemSetting[]>([]);
  isLoading = signal(true);
  errorMessage = signal('');
  /** Set de keys en update — deshabilita el toggle mientras hay PATCH
   *  in-flight para evitar dobles clicks. */
  saving = signal<Set<string>>(new Set());

  constructor(title: Title) {
    title.setTitle('SkilTak — Admin · Feature flags');
  }

  ngOnInit(): void {
    this.load();
  }

  private load(): void {
    this.isLoading.set(true);
    this.flagsService.listAdmin().subscribe({
      next: (list) => {
        this.flags.set(list);
        this.isLoading.set(false);
      },
      error: (err: HttpErrorResponse) => {
        console.error('Failed to load feature flags:', err);
        this.errorMessage.set(
          err.status === 403
            ? 'No tienes permisos para ver esta sección.'
            : 'No pudimos cargar los feature flags.',
        );
        this.isLoading.set(false);
      },
    });
  }

  isSaving(key: string): boolean {
    return this.saving().has(key);
  }

  toggle(flag: SystemSetting): void {
    if (this.isSaving(flag.key)) return;
    const next = !flag.value_bool;
    this.saving.update((s) => new Set(s).add(flag.key));
    this.flagsService.updateAdmin(flag.key, next).subscribe({
      next: (updated) => {
        // Reemplazar el flag en la lista para reflejar el nuevo estado +
        // updated_at fresco del backend.
        this.flags.update((list) =>
          list.map((f) => (f.key === updated.key ? updated : f)),
        );
        this.saving.update((s) => {
          const copy = new Set(s);
          copy.delete(flag.key);
          return copy;
        });
        this.toast.success(
          `${flag.key} ${next ? 'activado' : 'desactivado'}`,
        );
      },
      error: (err: HttpErrorResponse) => {
        console.error('Failed to toggle feature flag:', err);
        this.saving.update((s) => {
          const copy = new Set(s);
          copy.delete(flag.key);
          return copy;
        });
        this.toast.error('No pudimos actualizar el flag.');
      },
    });
  }

  /** Formato legible para el campo updated_at. */
  formatDate(iso: string): string {
    if (!iso) return '';
    try {
      return new Date(iso).toLocaleString('es', {
        dateStyle: 'medium',
        timeStyle: 'short',
      });
    } catch {
      return iso;
    }
  }
}

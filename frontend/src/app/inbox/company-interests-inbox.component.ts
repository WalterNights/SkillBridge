import { CommonModule } from '@angular/common';
import { HttpErrorResponse } from '@angular/common/http';
import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { Title } from '@angular/platform-browser';
import { RouterLink } from '@angular/router';

import {
  CompanyInterestRecord,
  CompanyInterestsService,
  RespondAction,
} from '../services/company-interests.service';
import { ToastService } from '../services/toast.service';

type StatusFilter = 'all' | 'pending' | 'accepted' | 'dismissed';

/**
 * Inbox del profesional: lista de empresas que marcaron interés en
 * su perfil. Tabs por status (Todas / Pendientes / Aceptadas /
 * Descartadas). Cada card permite aceptar o descartar pendientes.
 *
 * Privacidad: el email del responsable solo aparece cuando ya
 * aceptaste el interés — el backend hace el gating en el serializer.
 */
@Component({
  selector: 'app-company-interests-inbox',
  standalone: true,
  imports: [CommonModule, RouterLink],
  templateUrl: './company-interests-inbox.component.html',
  styleUrls: ['./company-interests-inbox.component.scss'],
})
export class CompanyInterestsInboxComponent implements OnInit {
  private service = inject(CompanyInterestsService);
  private toast = inject(ToastService);

  items = signal<CompanyInterestRecord[]>([]);
  total = signal(0);
  isLoading = signal(true);
  errorMessage = signal('');

  activeFilter = signal<StatusFilter>('all');
  /** Set de ids actualmente en flight (accept o dismiss) — usado para
   *  deshabilitar los botones por card. */
  pendingActions = signal<Set<number>>(new Set());

  readonly filterOptions: { value: StatusFilter; label: string }[] = [
    { value: 'all', label: 'Todas' },
    { value: 'pending', label: 'Pendientes' },
    { value: 'accepted', label: 'Aceptadas' },
    { value: 'dismissed', label: 'Descartadas' },
  ];

  /** Cantidad de pendientes — la mostramos en el badge del filtro. */
  pendingCount = computed(() =>
    this.items().filter((i) => i.status === 'pending').length,
  );

  constructor(title: Title) {
    title.setTitle('SkilTak — Empresas interesadas');
  }

  ngOnInit(): void {
    this.load();
  }

  load(): void {
    this.isLoading.set(true);
    this.errorMessage.set('');
    this.service.list(this.activeFilter()).subscribe({
      next: (res) => {
        this.items.set(res.results);
        this.total.set(res.total);
        this.isLoading.set(false);
      },
      error: (err: HttpErrorResponse) => {
        this.isLoading.set(false);
        if (err.status === 403) {
          this.errorMessage.set(
            'Este inbox es solo para cuentas profesional.',
          );
        } else {
          this.errorMessage.set('No pudimos cargar las empresas interesadas.');
        }
      },
    });
  }

  setFilter(value: StatusFilter): void {
    if (this.activeFilter() === value) return;
    this.activeFilter.set(value);
    this.load();
  }

  initials(name: string): string {
    return (name || '?').split(/\s+/).slice(0, 2).map((s) => s.charAt(0)).join('').toUpperCase();
  }

  isActionPending(id: number): boolean {
    return this.pendingActions().has(id);
  }

  respond(item: CompanyInterestRecord, action: RespondAction): void {
    const pending = new Set(this.pendingActions());
    pending.add(item.id);
    this.pendingActions.set(pending);

    this.service.respond(item.id, action).subscribe({
      next: (updated) => {
        const after = new Set(this.pendingActions());
        after.delete(item.id);
        this.pendingActions.set(after);

        // Reemplazar el item in-place. Si el filtro activo excluye
        // su nuevo status, lo sacamos del listado.
        this.items.update((rows) => {
          const filter = this.activeFilter();
          if (filter !== 'all' && updated.status !== filter) {
            return rows.filter((r) => r.id !== item.id);
          }
          return rows.map((r) => (r.id === item.id ? updated : r));
        });
        this.toast.success(
          action === 'accept'
            ? 'Aceptaste el interés. Ya podés contactar a la empresa.'
            : 'Interés descartado.',
        );
      },
      error: () => {
        const after = new Set(this.pendingActions());
        after.delete(item.id);
        this.pendingActions.set(after);
        this.toast.error('No pudimos completar la acción.');
      },
    });
  }

  trackItem(_index: number, item: CompanyInterestRecord): number {
    return item.id;
  }
}

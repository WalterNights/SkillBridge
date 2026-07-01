import { CommonModule } from '@angular/common';
import { Component, inject } from '@angular/core';
import { Title } from '@angular/platform-browser';
import { RouterLink } from '@angular/router';

import { AuthService } from '../../auth/auth.service';
import { PublicFooterComponent } from '../../shared/public-footer/public-footer.component';
import { PublicNavComponent } from '../../shared/public-nav/public-nav.component';
import {
  JOB_PORTALS,
  JobPortal,
  PORTAL_KIND_LABELS,
  PORTAL_KIND_ORDER,
} from './portales-data';

interface PortalGroup {
  kind: JobPortal['kind'];
  label: string;
  portals: JobPortal[];
}

/**
 * /portales — página informativa que lista los portales de empleo que
 * SkilTak scrapea. Objetivo: transparencia — que el usuario sepa dónde
 * estamos buscando ofertas para su perfil.
 *
 * Igual que /recursos, adapta el chrome según auth state: dentro del
 * AppShell (user autenticado) no dibuja PublicNav/PublicFooter; en el
 * fallback público sí.
 */
@Component({
  selector: 'app-portales',
  standalone: true,
  imports: [CommonModule, RouterLink, PublicNavComponent, PublicFooterComponent],
  templateUrl: './portales.component.html',
  styleUrl: './portales.component.scss',
})
export class PortalesComponent {
  readonly totalPortals = JOB_PORTALS.length;
  readonly groups: PortalGroup[] = PORTAL_KIND_ORDER.map((kind) => ({
    kind,
    label: PORTAL_KIND_LABELS[kind],
    portals: JOB_PORTALS.filter((p) => p.kind === kind),
  })).filter((g) => g.portals.length > 0);

  readonly insideShell: boolean;

  constructor(title: Title) {
    title.setTitle('Portales de empleo — de dónde vienen tus ofertas | SkilTak');
    this.insideShell = inject(AuthService).isAuthenticated();
  }
}

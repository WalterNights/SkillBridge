import { CommonModule } from '@angular/common';
import { Component, inject } from '@angular/core';
import { Title } from '@angular/platform-browser';
import { RouterLink } from '@angular/router';

import { AuthService } from '../../auth/auth.service';
import { PublicFooterComponent } from '../../shared/public-footer/public-footer.component';
import { PublicNavComponent } from '../../shared/public-nav/public-nav.component';

/**
 * /blog — placeholder honesto hasta que tengamos cadencia editorial real.
 *
 * Decision: en vez de listar 0 artículos o un "Coming soon" genérico,
 * redirigimos visualmente al index de /recursos donde sí hay contenido
 * útil. Cuando arranquemos a publicar posts cortos (newsletter style),
 * convertimos esta vista en el feed real.
 *
 * Si el user está auth, este componente vive dentro del AppShell — skip
 * PublicNav/PublicFooter para no duplicar chrome.
 */
@Component({
  selector: 'app-blog',
  standalone: true,
  imports: [CommonModule, RouterLink, PublicNavComponent, PublicFooterComponent],
  templateUrl: './blog.component.html',
})
export class BlogComponent {
  readonly insideShell: boolean;

  constructor(title: Title) {
    title.setTitle('Blog | SkilTak');
    this.insideShell = inject(AuthService).isAuthenticated();
  }
}

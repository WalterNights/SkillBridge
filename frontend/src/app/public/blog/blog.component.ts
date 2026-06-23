import { Component } from '@angular/core';
import { Title } from '@angular/platform-browser';
import { RouterLink } from '@angular/router';

import { PublicFooterComponent } from '../../shared/public-footer/public-footer.component';
import { PublicNavComponent } from '../../shared/public-nav/public-nav.component';

/**
 * /blog — placeholder honesto hasta que tengamos cadencia editorial real.
 *
 * Decision: en vez de listar 0 artículos o un "Coming soon" genérico,
 * redirigimos visualmente al index de /recursos donde sí hay contenido
 * útil. Cuando arranquemos a publicar posts cortos (newsletter style),
 * convertimos esta vista en el feed real.
 */
@Component({
  selector: 'app-blog',
  standalone: true,
  imports: [RouterLink, PublicNavComponent, PublicFooterComponent],
  templateUrl: './blog.component.html',
})
export class BlogComponent {
  constructor(title: Title) {
    title.setTitle('Blog | SkilTak');
  }
}

import {
  Component,
  ElementRef,
  HostBinding,
  HostListener,
  NgZone,
  OnDestroy,
  OnInit,
  computed,
  effect,
  inject,
  signal,
} from '@angular/core';
import { Title, Meta } from '@angular/platform-browser';
import { ActivatedRoute, RouterLink } from '@angular/router';

import { PortfolioI18nService } from '../i18n/portfolio-i18n.service';
import { PortfolioIconComponent } from '../components/portfolio-icon.component';
import { PortfolioSidebarComponent } from '../components/sidebar.component';
import {
  PortfolioImage,
  PortfolioService,
} from '../portfolio.service';
import { PortfolioProject } from '../sections/projects.component';

const PORTFOLIO_SLUG = 'walternightsdev';

/**
 * Vista de detalle de un proyecto — /portafolio/walternightsdev/proyectos/:id.
 *
 * Estructura idéntica al shell del portafolio (sidebar sticky + main
 * scrolleable) para que se sienta parte del mismo sitio, no una página
 * suelta. Reusa `PortfolioSidebarComponent` y las CSS vars scopeadas
 * (tipografía, paleta, cursor tracking).
 *
 * Ciclo de datos:
 * 1. Fetch de `getPublic(slug)` — mismo endpoint que el shell.
 * 2. Aplica el override i18n global (bundled + backend deep-merge).
 * 3. Busca el proyecto por :id. Si no existe → notFound(true), UI muestra
 *    mensaje amigable con link de vuelta.
 * 4. Filtra las imágenes del payload por `project_id === :id`.
 *
 * Bilingüe: los campos del proyecto se resuelven vía `i18n.raw()`, que
 * ya cambia reactivamente al togglear ES/EN. Los estructurales
 * (id/name/kind/status/stack/href/repo) son iguales en ambos idiomas
 * por la lógica `syncNonTranslatable` del editor.
 */
@Component({
  selector: 'app-project-detail',
  standalone: true,
  imports: [PortfolioSidebarComponent, PortfolioIconComponent, RouterLink],
  templateUrl: './project-detail.component.html',
  styleUrl: './project-detail.component.scss',
})
export class ProjectDetailComponent implements OnInit, OnDestroy {
  readonly i18n = inject(PortfolioI18nService);
  private readonly api = inject(PortfolioService);
  private readonly route = inject(ActivatedRoute);
  private readonly title = inject(Title);
  private readonly meta = inject(Meta);
  private readonly zone = inject(NgZone);
  private readonly host = inject(ElementRef<HTMLElement>);

  @HostBinding('class') hostClass = 'portfolio-scope';

  readonly loading = signal<boolean>(true);
  readonly notFound = signal<boolean>(false);

  /** ID del proyecto tomado de la URL. */
  readonly projectId = signal<string>('');

  /** Imágenes filtradas para este proyecto (todas, no solo la última). */
  readonly images = signal<PortfolioImage[]>([]);

  /** Proyecto resuelto reactivamente del i18n activo — cambia al togglear
   *  idioma sin re-fetch. */
  readonly project = computed<PortfolioProject | null>(() => {
    const id = this.projectId();
    if (!id) return null;
    const items = this.i18n.raw<PortfolioProject[]>('projects.items');
    if (!Array.isArray(items)) return null;
    return items.find((p) => p.id === id) ?? null;
  });

  /** Cerrado / abierto del lightbox + índice de imagen activa. */
  readonly lightboxIndex = signal<number | null>(null);

  private mouseMoveHandler: ((e: MouseEvent) => void) | null = null;

  constructor() {
    // <title> y <meta description> dinámicos por proyecto + idioma.
    effect(() => {
      const p = this.project();
      const langMeta = this.i18n.dict().meta;
      if (p) {
        this.title.setTitle(`${p.name} — ${langMeta.title}`);
        this.meta.updateTag({
          name: 'description',
          content: p.description || langMeta.description,
        });
      }
      document.documentElement.setAttribute('lang', this.i18n.lang());
    });
  }

  ngOnInit(): void {
    this.projectId.set(this.route.snapshot.paramMap.get('id') ?? '');
    this.fetch();
    this.attachCursorGlow();
  }

  ngOnDestroy(): void {
    if (this.mouseMoveHandler) {
      window.removeEventListener('mousemove', this.mouseMoveHandler);
      this.mouseMoveHandler = null;
    }
  }

  private fetch(): void {
    this.loading.set(true);
    this.notFound.set(false);
    this.api.getPublic(PORTFOLIO_SLUG).subscribe({
      next: (payload) => {
        this.i18n.applyBackendContent({
          es: payload.content,
          en: payload.content_en,
          images: payload.images,
        });
        const id = this.projectId();
        this.images.set(payload.images.filter((img) => img.project_id === id));
        // Verificamos existencia del proyecto en el diccionario ES (source
        // of truth de estructura). Si no está → 404 amigable.
        const es = (payload.content?.['projects'] as Record<string, unknown>)?.[
          'items'
        ] as PortfolioProject[] | undefined;
        const exists = Array.isArray(es) && es.some((p) => p.id === id);
        this.notFound.set(!exists);
        this.loading.set(false);
      },
      error: () => {
        this.notFound.set(true);
        this.loading.set(false);
      },
    });
  }

  // ─── Lightbox ────────────────────────────────────────────────────
  openLightbox(index: number): void {
    this.lightboxIndex.set(index);
    document.body.style.overflow = 'hidden';
  }

  closeLightbox(): void {
    this.lightboxIndex.set(null);
    document.body.style.overflow = '';
  }

  nextImage(): void {
    const i = this.lightboxIndex();
    if (i === null) return;
    const total = this.images().length;
    if (total === 0) return;
    this.lightboxIndex.set((i + 1) % total);
  }

  prevImage(): void {
    const i = this.lightboxIndex();
    if (i === null) return;
    const total = this.images().length;
    if (total === 0) return;
    this.lightboxIndex.set((i - 1 + total) % total);
  }

  @HostListener('window:keydown', ['$event'])
  onKey(event: KeyboardEvent): void {
    if (this.lightboxIndex() === null) return;
    if (event.key === 'Escape') this.closeLightbox();
    else if (event.key === 'ArrowRight') this.nextImage();
    else if (event.key === 'ArrowLeft') this.prevImage();
  }

  // ─── Cursor glow (reusa la técnica del shell) ────────────────────
  private attachCursorGlow(): void {
    if (typeof window === 'undefined') return;
    if (!window.matchMedia('(hover: hover) and (pointer: fine)').matches) return;
    const hostEl = this.host.nativeElement;
    this.zone.runOutsideAngular(() => {
      this.mouseMoveHandler = (e: MouseEvent) => {
        hostEl.style.setProperty('--pf-mx', `${e.clientX}px`);
        hostEl.style.setProperty('--pf-my', `${e.clientY}px`);
      };
      window.addEventListener('mousemove', this.mouseMoveHandler, { passive: true });
    });
  }

  // ─── Helpers de template ─────────────────────────────────────────
  labelOf(key: string): string {
    return this.i18n.t(`projects.labels.${key}`);
  }
}

import { CommonModule } from '@angular/common';
import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { CdkDrag, CdkDragDrop, CdkDropList } from '@angular/cdk/drag-drop';
import {
  FormArray,
  FormBuilder,
  FormControl,
  FormGroup,
  ReactiveFormsModule,
  Validators,
} from '@angular/forms';
import { Title } from '@angular/platform-browser';
import { Router } from '@angular/router';

import {
  PortfolioImage,
  PortfolioService,
  PortfolioAdminPayload,
} from '../portfolio.service';
import {
  SOCIAL_ICONS,
  TECH_ICONS,
  findIconById,
  searchTechIcons,
  PortfolioIcon,
} from '../data/portfolio-icons.data';
import { PortfolioIconComponent } from '../components/portfolio-icon.component';

const SLUG = 'walternightsdev';

type SectionTab =
  | 'meta'
  | 'sidebar'
  | 'hero'
  | 'about'
  | 'experience'
  | 'projects'
  | 'contact'
  | 'footer';

const TABS: readonly { id: SectionTab; label: string }[] = [
  { id: 'hero', label: 'Hero' },
  { id: 'about', label: 'Sobre mí' },
  { id: 'experience', label: 'Experiencia' },
  { id: 'projects', label: 'Proyectos' },
  { id: 'contact', label: 'Contacto' },
  { id: 'sidebar', label: 'Sidebar' },
  { id: 'meta', label: 'Meta / SEO' },
  { id: 'footer', label: 'Footer' },
];

/**
 * Editor admin del portafolio `walternightsdev`.
 *
 * Dos FormGroups paralelos con la misma shape (`formEs` y `formEn`) —
 * un tab por sección, y para cada string traducible se muestran dos
 * inputs side-by-side (ES / EN). Los campos no-traducibles (id, kind,
 * status, stack, urls, etc.) viven solo en `formEs`; al guardar,
 * `buildPayload()` los duplica en el árbol EN para que el backend
 * reciba ambos content coherentes.
 *
 * Arrays (paragraphs, experience items, projects items) van con
 * FormArray. Add/remove operan sobre AMBOS forms al mismo tiempo para
 * mantener índices sincronizados — el proyecto en `formEs.items[0]` es
 * el mismo objeto que `formEn.items[0]`.
 */
@Component({
  selector: 'app-portfolio-editor',
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    PortfolioIconComponent,
    CdkDropList,
    CdkDrag,
  ],
  templateUrl: './portfolio-editor.component.html',
  styleUrl: './portfolio-editor.component.scss',
})
export class PortfolioEditorComponent implements OnInit {
  private fb = inject(FormBuilder);
  private api = inject(PortfolioService);
  private router = inject(Router);
  private titleService = inject(Title);

  readonly tabs = TABS;
  readonly activeTab = signal<SectionTab>('hero');

  readonly loading = signal<boolean>(true);
  readonly saving = signal<boolean>(false);
  readonly successMsg = signal<string>('');
  readonly errorMsg = signal<string>('');

  readonly images = signal<PortfolioImage[]>([]);
  readonly uploading = signal<string | null>(null); // project_id que está subiendo

  formEs: FormGroup = this.buildForm();
  formEn: FormGroup = this.buildForm();

  // ── Icon pickers ──────────────────────────────────────────────────
  /** Socials agrupados por categoría — para <optgroup> del dropdown. */
  readonly socialGroups: readonly { label: string; icons: readonly PortfolioIcon[] }[] = [
    { label: 'Dev platforms', icons: SOCIAL_ICONS.filter((i) => i.category === 'developer') },
    { label: 'Redes sociales', icons: SOCIAL_ICONS.filter((i) => i.category === 'social') },
    { label: 'Creative / Publishing', icons: SOCIAL_ICONS.filter((i) => i.category === 'creative') },
    { label: 'Contacto', icons: SOCIAL_ICONS.filter((i) => i.category === 'contact') },
  ];

  /** Query del autocomplete de tech + resultados filtrados. */
  readonly techQuery = signal<string>('');
  readonly techSuggestions = computed(() => searchTechIcons(this.techQuery()));

  ngOnInit(): void {
    this.titleService.setTitle('Editar portafolio — SkilTak');
    this.load();
  }

  // ═══════════════════════════════════════════════════════════════════
  // Form skeleton — misma shape para ES y EN
  // ═══════════════════════════════════════════════════════════════════
  private buildForm(): FormGroup {
    return this.fb.group({
      meta: this.fb.group({
        title: [''],
        description: [''],
      }),
      sidebar: this.fb.group({
        role: [''],
        tagline: [''],
        techLabel: [''],
        nav: this.fb.group({
          about: [''],
          experience: [''],
          projects: [''],
          contact: [''],
        }),
        // socials + tech: NO traducibles. Los editamos SOLO en formEs
        // y en save() se copian al content_en. Formas paralelas serían
        // desperdicio + fuente de bugs (arrays desincronizados).
        socials: this.fb.array<FormGroup>([]),
        tech: this.fb.array<FormControl<string>>([]),
      }),
      hero: this.fb.group({
        eyebrow: [''],
        titleTop: [''],
        titleBottom: [''],
        subtitle: [''],
        cta: this.fb.group({
          projects: [''],
          contact: [''],
        }),
      }),
      about: this.fb.group({
        eyebrow: [''],
        title: [''],
        paragraphs: this.fb.array<FormControl<string>>([]),
      }),
      experience: this.fb.group({
        eyebrow: [''],
        title: [''],
        items: this.fb.array<FormGroup>([]),
      }),
      projects: this.fb.group({
        eyebrow: [''],
        title: [''],
        note: [''],
        filters: this.fb.group({ all: [''], personal: [''], enterprise: [''] }),
        labels: this.fb.group({
          personal: [''], enterprise: [''],
          live: [''], private: [''], wip: [''],
          viewSite: [''], viewRepo: [''], screenshot: [''],
        }),
        items: this.fb.array<FormGroup>([]),
      }),
      contact: this.fb.group({
        eyebrow: [''],
        title: [''],
        body: [''],
        cta: [''],
        email: [''],
      }),
      footer: this.fb.group({
        built: [''],
        stack: [''],
      }),
      langToggle: this.fb.group({
        label: [''],
        es: [''],
        en: [''],
      }),
    });
  }

  private buildExperienceItem(seed: Record<string, unknown> = {}): FormGroup {
    return this.fb.group({
      period: [seed['period'] ?? ''],
      role: [seed['role'] ?? ''],
      company: [seed['company'] ?? ''],
      url: [seed['url'] ?? ''],
      description: [seed['description'] ?? ''],
      stack: [Array.isArray(seed['stack']) ? (seed['stack'] as string[]).join(', ') : ''],
    });
  }

  private buildSocialItem(id: string, url: string): FormGroup {
    return this.fb.group({
      id: [id, Validators.required],
      url: [url],
    });
  }

  private buildProjectItem(seed: Record<string, unknown> = {}): FormGroup {
    return this.fb.group({
      id: [seed['id'] ?? '', Validators.required],
      name: [seed['name'] ?? ''],
      kind: [seed['kind'] ?? 'personal'],
      status: [seed['status'] ?? 'live'],
      description: [seed['description'] ?? ''],
      stack: [Array.isArray(seed['stack']) ? (seed['stack'] as string[]).join(', ') : ''],
      href: [seed['href'] ?? ''],
      repo: [seed['repo'] ?? ''],
    });
  }

  // ═══════════════════════════════════════════════════════════════════
  // Load: hidrata ambos forms desde el backend
  // ═══════════════════════════════════════════════════════════════════
  private load(): void {
    this.loading.set(true);
    this.api.getAdmin(SLUG).subscribe({
      next: (payload) => {
        this.images.set(payload.images);
        this.hydrateForm(this.formEs, payload.content);
        this.hydrateForm(this.formEn, payload.content_en);
        this.loading.set(false);
      },
      error: () => {
        this.errorMsg.set('No se pudo cargar el portafolio. Verificá tu sesión.');
        this.loading.set(false);
      },
    });
  }

  private hydrateForm(form: FormGroup, content: Record<string, unknown>): void {
    // patchValue ignora keys que no existen en el form — perfecto para
    // hidratar sin romper si el backend agrega campos nuevos.
    form.patchValue(content);

    // Arrays: patchValue no expande FormArrays, hay que reconstruir.
    const about = (content['about'] as Record<string, unknown>) ?? {};
    const paragraphs = (about['paragraphs'] as string[]) ?? [];
    const paragraphsArr = (form.get('about.paragraphs') as FormArray);
    paragraphsArr.clear();
    paragraphs.forEach((p) => paragraphsArr.push(new FormControl(p, { nonNullable: true })));

    // Socials — solo en formEs (no traducible). En formEn los arrays
    // quedan vacíos y se llenan desde ES en save().
    if (form === this.formEs) {
      const sidebar = (content['sidebar'] as Record<string, unknown>) ?? {};
      const socialsData = (sidebar['socials'] as { id: string; url: string }[]) ?? [];
      const socialsArr = form.get('sidebar.socials') as FormArray;
      socialsArr.clear();
      socialsData.forEach((s) =>
        socialsArr.push(this.buildSocialItem(s.id ?? '', s.url ?? '')),
      );

      const techData = (sidebar['tech'] as string[]) ?? [];
      const techArr = form.get('sidebar.tech') as FormArray;
      techArr.clear();
      techData.forEach((t) => techArr.push(new FormControl(t, { nonNullable: true })));
    }

    const exp = (content['experience'] as Record<string, unknown>) ?? {};
    const expItems = (exp['items'] as Record<string, unknown>[]) ?? [];
    const expArr = form.get('experience.items') as FormArray;
    expArr.clear();
    expItems.forEach((item) => expArr.push(this.buildExperienceItem(item)));

    const proj = (content['projects'] as Record<string, unknown>) ?? {};
    const projItems = (proj['items'] as Record<string, unknown>[]) ?? [];
    const projArr = form.get('projects.items') as FormArray;
    projArr.clear();
    projItems.forEach((item) => projArr.push(this.buildProjectItem(item)));
  }

  // ═══════════════════════════════════════════════════════════════════
  // Getters para el template (FormArrays tipadas)
  // ═══════════════════════════════════════════════════════════════════
  get paragraphsEs(): FormArray {
    return this.formEs.get('about.paragraphs') as FormArray;
  }
  get paragraphsEn(): FormArray {
    return this.formEn.get('about.paragraphs') as FormArray;
  }
  get experienceItemsEs(): FormArray {
    return this.formEs.get('experience.items') as FormArray;
  }
  get experienceItemsEn(): FormArray {
    return this.formEn.get('experience.items') as FormArray;
  }
  get projectItemsEs(): FormArray {
    return this.formEs.get('projects.items') as FormArray;
  }
  get projectItemsEn(): FormArray {
    return this.formEn.get('projects.items') as FormArray;
  }

  paragraphEsCtrl(i: number): FormControl {
    return this.paragraphsEs.at(i) as FormControl;
  }
  paragraphEnCtrl(i: number): FormControl {
    return this.paragraphsEn.at(i) as FormControl;
  }
  expItemEs(i: number): FormGroup {
    return this.experienceItemsEs.at(i) as FormGroup;
  }
  expItemEn(i: number): FormGroup {
    return this.experienceItemsEn.at(i) as FormGroup;
  }
  projItemEs(i: number): FormGroup {
    return this.projectItemsEs.at(i) as FormGroup;
  }
  projItemEn(i: number): FormGroup {
    return this.projectItemsEn.at(i) as FormGroup;
  }

  // ═══════════════════════════════════════════════════════════════════
  // Array ops — operan sobre AMBOS forms en paralelo
  // ═══════════════════════════════════════════════════════════════════
  addParagraph(): void {
    this.paragraphsEs.push(new FormControl('', { nonNullable: true }));
    this.paragraphsEn.push(new FormControl('', { nonNullable: true }));
  }

  removeParagraph(i: number): void {
    this.paragraphsEs.removeAt(i);
    this.paragraphsEn.removeAt(i);
  }

  addExperience(): void {
    this.experienceItemsEs.push(this.buildExperienceItem());
    this.experienceItemsEn.push(this.buildExperienceItem());
  }

  removeExperience(i: number): void {
    this.experienceItemsEs.removeAt(i);
    this.experienceItemsEn.removeAt(i);
  }

  addProject(): void {
    // Generamos un id provisorio — el user debe editarlo antes de guardar.
    const newId = `proyecto-${Date.now().toString(36).slice(-5)}`;
    this.projectItemsEs.push(this.buildProjectItem({ id: newId }));
    this.projectItemsEn.push(this.buildProjectItem({ id: newId }));
  }

  removeProject(i: number): void {
    this.projectItemsEs.removeAt(i);
    this.projectItemsEn.removeAt(i);
  }

  // ═══════════════════════════════════════════════════════════════════
  // Socials + Tech (viven solo en formEs, se sincronizan a EN al save)
  // ═══════════════════════════════════════════════════════════════════

  get socialsArr(): FormArray {
    return this.formEs.get('sidebar.socials') as FormArray;
  }

  get techArr(): FormArray {
    return this.formEs.get('sidebar.tech') as FormArray;
  }

  socialItem(i: number): FormGroup {
    return this.socialsArr.at(i) as FormGroup;
  }

  techCtrl(i: number): FormControl {
    return this.techArr.at(i) as FormControl;
  }

  addSocial(): void {
    this.socialsArr.push(this.buildSocialItem('github', ''));
  }

  removeSocial(i: number): void {
    this.socialsArr.removeAt(i);
  }

  /** Actualiza el placeholder de URL según el icono seleccionado. */
  hintForSocial(id: string): string {
    return findIconById(id)?.hint ?? 'https://';
  }

  /** Agrega un tech por id, si existe en el catálogo y no está repetido. */
  addTech(id: string): void {
    const trimmed = id.trim().toLowerCase();
    if (!trimmed) return;
    const def = findIconById(trimmed);
    if (!def) {
      this.errorMsg.set(`No hay icono para "${trimmed}". Elegí uno de la lista.`);
      setTimeout(() => this.errorMsg.set(''), 3000);
      return;
    }
    // Evitar duplicados.
    const existing = this.techArr.controls.map((c) => c.value as string);
    if (existing.includes(trimmed)) return;
    this.techArr.push(new FormControl(trimmed, { nonNullable: true }));
    this.techQuery.set('');
  }

  removeTech(i: number): void {
    this.techArr.removeAt(i);
  }

  /** Reordena el FormArray al soltar el chip en otra posición.
   *  Movemos el CONTROL (no el valor) — preserva la referencia y evita
   *  disparar valueChanges innecesarios en cada chip afectado. */
  onTechDrop(event: CdkDragDrop<unknown>): void {
    if (event.previousIndex === event.currentIndex) return;
    const ctrl = this.techArr.at(event.previousIndex);
    this.techArr.removeAt(event.previousIndex, { emitEvent: false });
    this.techArr.insert(event.currentIndex, ctrl, { emitEvent: false });
    // Un solo emit al final: notifica que el array cambió sin generar
    // N eventos por chip.
    this.techArr.updateValueAndValidity();
  }

  onTechInputChange(value: string): void {
    this.techQuery.set(value);
  }

  /** Cuando el user aprieta Enter en el input, agrega el primer match. */
  onTechInputEnter(event: Event): void {
    event.preventDefault();
    const first = this.techSuggestions()[0];
    if (first) this.addTech(first.id);
  }

  /** Nombre de un tech id — para mostrar en los chips. */
  techName(id: string): string {
    return findIconById(id)?.name ?? id;
  }

  // ═══════════════════════════════════════════════════════════════════
  // Imágenes
  // ═══════════════════════════════════════════════════════════════════
  imageForProject(projectId: string): PortfolioImage | undefined {
    // Última subida gana (backend ordena por -created_at).
    return this.images().find((img) => img.project_id === projectId);
  }

  onCoverSelected(event: Event, projectId: string): void {
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0];
    if (!file) return;
    if (!projectId) {
      this.errorMsg.set('El proyecto necesita un `id` antes de subir imagen.');
      return;
    }
    this.uploading.set(projectId);
    this.errorMsg.set('');
    this.api.uploadImage(SLUG, file, projectId).subscribe({
      next: (img) => {
        // Reemplazamos cualquier imagen previa del mismo project_id en el
        // signal local; el backend ordena por -created_at, así que la
        // más nueva termina ganando en el shell público.
        this.images.update((current) => [
          img,
          ...current.filter((i) => i.project_id !== projectId),
        ]);
        this.uploading.set(null);
        this.successMsg.set(`Captura de "${projectId}" subida.`);
        setTimeout(() => this.successMsg.set(''), 3500);
      },
      error: (err) => {
        this.uploading.set(null);
        this.errorMsg.set(
          err?.error?.image?.[0] ?? err?.error?.detail ?? 'Error al subir la imagen.',
        );
      },
    });
    input.value = ''; // permite re-seleccionar el mismo archivo si falla
  }

  deleteCover(projectId: string): void {
    const img = this.imageForProject(projectId);
    if (!img) return;
    if (!confirm(`¿Borrar la captura de "${projectId}"?`)) return;
    this.api.deleteImage(SLUG, img.id).subscribe({
      next: () => {
        this.images.update((current) => current.filter((i) => i.id !== img.id));
      },
      error: () => {
        this.errorMsg.set('No se pudo borrar la imagen.');
      },
    });
  }

  // ═══════════════════════════════════════════════════════════════════
  // Guardar
  // ═══════════════════════════════════════════════════════════════════

  /** Convierte los dos FormGroups en el payload {content, content_en}
   *  que espera el backend. Duplica campos no-traducibles del ES al EN. */
  private buildPayload(): { content: Record<string, unknown>; content_en: Record<string, unknown> } {
    const content = this.serializeSide(this.formEs);
    const content_en = this.serializeSide(this.formEn);
    // Copia de campos NO traducibles desde ES → EN (para que ambos árboles
    // queden coherentes y el backend no exponga datos divergentes).
    // Simplificación: para los items de experience/projects, los campos
    // estructurales (id/kind/status/href/repo/url/period/stack) los
    // dictamos desde ES.
    this.syncNonTranslatable(content, content_en);
    return { content, content_en };
  }

  private serializeSide(form: FormGroup): Record<string, unknown> {
    const raw = form.getRawValue() as Record<string, unknown>;
    // Convertimos `stack` (string CSV) a array de strings para experience y projects.
    const exp = raw['experience'] as Record<string, unknown>;
    if (exp && Array.isArray(exp['items'])) {
      exp['items'] = (exp['items'] as Record<string, unknown>[]).map((it) => ({
        ...it,
        stack: this.csvToArray(it['stack'] as string),
      }));
    }
    const proj = raw['projects'] as Record<string, unknown>;
    if (proj && Array.isArray(proj['items'])) {
      proj['items'] = (proj['items'] as Record<string, unknown>[]).map((it) => ({
        ...it,
        stack: this.csvToArray(it['stack'] as string),
      }));
    }
    return raw;
  }

  private csvToArray(value: string): string[] {
    if (!value) return [];
    return value
      .split(',')
      .map((s) => s.trim())
      .filter((s) => s.length > 0);
  }

  private syncNonTranslatable(
    src: Record<string, unknown>,
    dst: Record<string, unknown>,
  ): void {
    // Sidebar socials + tech: copiamos completo de ES → EN (no
    // traducibles). El editor solo los muestra/edita en ES.
    const srcSidebar = (src['sidebar'] as Record<string, unknown>) ?? {};
    const dstSidebar = (dst['sidebar'] as Record<string, unknown>) ?? {};
    dstSidebar['socials'] = srcSidebar['socials'] ?? [];
    dstSidebar['tech'] = srcSidebar['tech'] ?? [];

    const srcExp = ((src['experience'] as Record<string, unknown>)?.['items'] as Record<string, unknown>[]) ?? [];
    const dstExpParent = (dst['experience'] as Record<string, unknown>) ?? {};
    const dstExp = (dstExpParent['items'] as Record<string, unknown>[]) ?? [];
    srcExp.forEach((item, i) => {
      if (!dstExp[i]) return;
      dstExp[i]['period'] = item['period'];
      dstExp[i]['company'] = item['company'];
      dstExp[i]['url'] = item['url'];
      dstExp[i]['stack'] = item['stack'];
      // `role` puede querer traducirse (ej. "Desarrollador" vs "Developer")
      // — se deja editable en cada idioma. Idem `description`.
    });

    const srcProj = ((src['projects'] as Record<string, unknown>)?.['items'] as Record<string, unknown>[]) ?? [];
    const dstProjParent = (dst['projects'] as Record<string, unknown>) ?? {};
    const dstProj = (dstProjParent['items'] as Record<string, unknown>[]) ?? [];
    srcProj.forEach((item, i) => {
      if (!dstProj[i]) return;
      dstProj[i]['id'] = item['id'];
      dstProj[i]['name'] = item['name'];
      dstProj[i]['kind'] = item['kind'];
      dstProj[i]['status'] = item['status'];
      dstProj[i]['stack'] = item['stack'];
      dstProj[i]['href'] = item['href'];
      dstProj[i]['repo'] = item['repo'];
      // `description` sí se traduce.
    });
  }

  save(): void {
    this.errorMsg.set('');
    this.successMsg.set('');
    this.saving.set(true);
    const payload = this.buildPayload();
    this.api.updateAdmin(SLUG, payload).subscribe({
      next: () => {
        this.saving.set(false);
        this.successMsg.set('Portafolio guardado. Los cambios ya se ven en la ruta pública.');
        setTimeout(() => this.successMsg.set(''), 4000);
      },
      error: (err) => {
        this.saving.set(false);
        this.errorMsg.set(
          err?.error?.detail ?? 'Error al guardar. Revisá los campos e intentá de nuevo.',
        );
      },
    });
  }

  openPublic(): void {
    window.open(`/portafolio/${SLUG}`, '_blank', 'noopener');
  }

  goBack(): void {
    this.router.navigate(['/me']);
  }

  setTab(tab: SectionTab): void {
    this.activeTab.set(tab);
  }
}

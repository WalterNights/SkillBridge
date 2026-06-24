import { CommonModule } from '@angular/common';
import {
  Component,
  ElementRef,
  EmbeddedViewRef,
  EventEmitter,
  HostListener,
  Input,
  OnDestroy,
  Output,
  TemplateRef,
  ViewChild,
  ViewContainerRef,
  computed,
  inject,
  signal,
} from '@angular/core';

export interface SelectOption {
  value: string;
  label: string;
}

/**
 * Dropdown custom para reemplazar `<select>` nativo donde necesitamos
 * tema dark consistente. El `<select>` nativo abre un panel cuyas
 * `<option>` y hover-state heredan del OS — sobre dark theme queda feo
 * (panel blanco con hover azul system).
 *
 * Diseño:
 *   - Trigger button con el label de la opción seleccionada + chevron
 *   - Panel renderizado como child de document.body (portal manual) para
 *     escapar containing blocks creados por ancestros con `backdrop-filter`
 *     (caso típico de las cards `.glass-strong`). Sin el portal, el panel
 *     queda atado al card padre y `position:fixed` con coords del viewport
 *     se ofsetea — visualmente el panel cae lejos del trigger.
 *   - Cada opción es un button con hover naranja del brand
 *   - La seleccionada tiene checkmark
 *   - Click fuera o ESC cierra
 *
 * No soporta búsqueda ni grupos — solo lista plana. Si más adelante se
 * necesita, agregar un Input adicional sin breaking change.
 *
 * Uso:
 *   <app-select
 *     [options]="[{value:'es', label:'Español'}, ...]"
 *     [(value)]="lang"
 *     placeholder="Seleccioná un idioma"
 *   />
 */
@Component({
  selector: 'app-select',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './select.component.html',
  styleUrls: ['./select.component.scss'],
})
export class SelectComponent implements OnDestroy {
  @Input({ required: true }) options: SelectOption[] = [];
  @Input() value = '';
  @Output() valueChange = new EventEmitter<string>();
  @Input() placeholder = 'Seleccioná una opción';
  /** Anchura del trigger (por default 100% del contenedor). */
  @Input() widthClass = 'w-full';

  open = signal(false);

  /** Coordenadas del panel — se setean justo antes de abrir. */
  panelTop = '0px';
  panelLeft = '0px';
  panelWidth = '0px';

  selectedLabel = computed(() => {
    const v = this.value;
    return this.options.find((o) => o.value === v)?.label ?? this.placeholder;
  });

  private hostEl = inject(ElementRef);
  private vcr = inject(ViewContainerRef);
  @ViewChild('trigger', { static: true }) triggerRef!: ElementRef<HTMLButtonElement>;
  @ViewChild('panelTpl', { static: true }) panelTpl!: TemplateRef<unknown>;

  /** Vista embebida del panel — vive en document.body cuando está abierto. */
  private embeddedView?: EmbeddedViewRef<unknown>;

  ngOnDestroy(): void {
    this.destroyPanel();
  }

  toggle(event?: Event): void {
    event?.stopPropagation();
    if (this.open()) {
      this.closePanel();
      return;
    }
    this.openPanel();
  }

  private openPanel(): void {
    this.computePanelPosition();
    this.embeddedView = this.vcr.createEmbeddedView(this.panelTpl);
    // Mover los root nodes al body — escapa cualquier containing block
    // que ancestros con backdrop-filter, transform, will-change, etc.
    // hayan creado.
    this.embeddedView.rootNodes.forEach((node: Node) => {
      if (node instanceof HTMLElement) {
        document.body.appendChild(node);
      }
    });
    this.embeddedView.detectChanges();
    this.open.set(true);
  }

  private closePanel(): void {
    this.destroyPanel();
    this.open.set(false);
  }

  private destroyPanel(): void {
    if (!this.embeddedView) return;
    // rootNodes ya fue moved a body; destroy() los va a remover del DOM
    // y limpiar bindings.
    this.embeddedView.destroy();
    this.embeddedView = undefined;
  }

  private computePanelPosition(): void {
    const btn = this.triggerRef?.nativeElement;
    if (!btn) return;
    const rect = btn.getBoundingClientRect();
    this.panelTop = `${rect.bottom + 6}px`;
    this.panelLeft = `${rect.left}px`;
    this.panelWidth = `${rect.width}px`;
  }

  pick(event: Event, option: SelectOption): void {
    event.stopPropagation();
    if (option.value !== this.value) {
      this.value = option.value;
      this.valueChange.emit(option.value);
    }
    this.closePanel();
  }

  isSelected(option: SelectOption): boolean {
    return option.value === this.value;
  }

  /** Cierre al mousedown fuera del host O fuera del panel. Usamos
   *  mousedown en vez de click porque (click) en Angular pasa por event
   *  delegation a document y podía fire antes que el componente actualice
   *  su signal — ahora chequeamos AMBOS el host y el panel (que ya no es
   *  descendiente del host porque está en body). */
  @HostListener('document:mousedown', ['$event'])
  onDocMouseDown(event: MouseEvent): void {
    if (!this.open()) return;
    const target = event.target as Node;
    const inHost = this.hostEl.nativeElement.contains(target);
    const inPanel = this.embeddedView?.rootNodes.some((node: Node) =>
      node instanceof HTMLElement ? node.contains(target) : false,
    );
    if (!inHost && !inPanel) {
      this.closePanel();
    }
  }

  /** Cierre con ESC. */
  @HostListener('document:keydown.escape')
  onEscape(): void {
    if (this.open()) this.closePanel();
  }
}

import { CommonModule } from '@angular/common';
import {
  Component,
  EventEmitter,
  Input,
  OnInit,
  Output,
  inject,
  signal,
} from '@angular/core';
import { FormsModule } from '@angular/forms';

import { QuantifyService } from '../services/quantify.service';
import { ToastService } from '../services/toast.service';

type ViewMode = 'loading' | 'ready' | 'error';

/**
 * Modal: "Cuantificar logro con AI".
 *
 * Toma un bullet de experiencia, llama al backend (Gemini), muestra 3
 * variantes cuantificadas con números/métricas. El user elige una (o
 * edita el textarea manualmente) y emite `applied` con el texto final.
 *
 * No persiste por sí mismo — el componente padre se encarga de hacer
 * el PATCH al profile y refrescar la vista.
 */
@Component({
  selector: 'app-quantify-modal',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './quantify-modal.component.html',
  styleUrls: ['./quantify-modal.component.scss'],
})
export class QuantifyModalComponent implements OnInit {
  @Input({ required: true }) originalText!: string;
  /** Contexto opcional del rol — mejora la calidad de las sugerencias. */
  @Input() roleTitle = '';
  @Input() company = '';

  /** El padre escucha — recibe el texto final que el user aceptó. */
  @Output() applied = new EventEmitter<string>();
  @Output() closed = new EventEmitter<void>();

  view = signal<ViewMode>('loading');
  suggestions = signal<string[]>([]);
  /** Variante seleccionada (índice). null = ninguna, el user va a editar
   * el textarea desde cero o desde el original. */
  selectedIndex = signal<number | null>(null);
  /** Contenido del textarea — empieza vacío, se llena al elegir una variante. */
  editorContent = '';
  errorMsg = '';

  private api = inject(QuantifyService);
  private toast = inject(ToastService);

  ngOnInit(): void {
    this.fetchSuggestions();
  }

  fetchSuggestions(): void {
    this.view.set('loading');
    this.errorMsg = '';
    this.api.suggest(this.originalText, this.roleTitle, this.company).subscribe({
      next: (res) => {
        this.suggestions.set(res.suggestions || []);
        // Pre-seleccionamos la primera para que el user vea contenido
        // editable al instante en vez de un textarea vacío.
        if (res.suggestions?.length) {
          this.selectVariant(0);
        }
        this.view.set('ready');
      },
      error: (err) => {
        const detail = err?.error?.detail || 'No pudimos generar sugerencias. Intentá de nuevo.';
        this.errorMsg = detail;
        this.view.set('error');
      },
    });
  }

  selectVariant(index: number): void {
    this.selectedIndex.set(index);
    this.editorContent = this.suggestions()[index] || '';
  }

  apply(): void {
    const text = this.editorContent.trim();
    if (!text) {
      this.toast.error('No podés guardar un texto vacío.');
      return;
    }
    if (text === this.originalText.trim()) {
      this.toast.info('No cambiaste nada — cerrando.');
      this.close();
      return;
    }
    this.applied.emit(text);
  }

  regenerate(): void {
    this.fetchSuggestions();
  }

  close(): void {
    this.closed.emit();
  }
}

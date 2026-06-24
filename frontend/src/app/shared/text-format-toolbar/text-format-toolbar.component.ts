import { CommonModule } from '@angular/common';
import {
  Component,
  ElementRef,
  HostListener,
  OnDestroy,
  OnInit,
  signal,
} from '@angular/core';

/**
 * Toolbar flotante que aplica formato Markdown-like a la selección
 * activa del último `<textarea class="rich-textarea">` que tuvo focus.
 *
 * Por qué markdown y no rich text real:
 *   - Las textareas son plain-text (input type=textarea). Convertir a
 *     contenteditable + rich editor (Quill, TipTap) requiere reescribir
 *     todos los campos del form de /me.
 *   - El backend almacena experience/education/summary como TextField.
 *     Markdown viaja como cualquier otro string.
 *   - El render en /cv ya parsea bullets con prefijo "- " / "• " / "* ".
 *     Bold/italic se ven como "**texto**" en el editor pero quedan
 *     parseables para una pasada futura del render.
 *
 * Cómo se conecta:
 *   1. El componente padre incluye `<app-text-format-toolbar />`.
 *   2. El componente listenea `focusin` globales y guarda referencia al
 *      último <textarea.rich-textarea> activo.
 *   3. Cuando el user clickea un botón, leemos selectionStart/End del
 *      textarea, mutamos el value alrededor de la selección, y
 *      disparamos un Input event para que Angular Forms recoja el
 *      cambio sin tener que importar FormControl.
 */
@Component({
  selector: 'app-text-format-toolbar',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './text-format-toolbar.component.html',
  styleUrls: ['./text-format-toolbar.component.scss'],
})
export class TextFormatToolbarComponent implements OnInit, OnDestroy {
  /** True cuando hay un textarea activo — el toolbar se ilumina. */
  hasActiveTarget = signal(false);

  private activeTextarea: HTMLTextAreaElement | null = null;
  private focusHandler = (e: FocusEvent) => this.onGlobalFocus(e);
  private blurHandler = () => {
    // Pequeño delay para que el click en un botón del toolbar no se pierda.
    setTimeout(() => {
      if (document.activeElement !== this.activeTextarea) {
        // No invalido la referencia — queremos que el user pueda volver
        // a clickear botones aunque el textarea perdió focus. Solo el
        // indicador visual baja.
        this.hasActiveTarget.set(false);
      }
    }, 150);
  };

  ngOnInit(): void {
    document.addEventListener('focusin', this.focusHandler);
    document.addEventListener('focusout', this.blurHandler);
  }

  ngOnDestroy(): void {
    document.removeEventListener('focusin', this.focusHandler);
    document.removeEventListener('focusout', this.blurHandler);
  }

  private onGlobalFocus(event: FocusEvent): void {
    const target = event.target as HTMLElement | null;
    if (target instanceof HTMLTextAreaElement && target.classList.contains('rich-textarea')) {
      this.activeTextarea = target;
      this.hasActiveTarget.set(true);
    }
  }

  // ---- Acciones de formato -----------------------------------------

  bold(): void {
    this.wrapSelection('**', '**');
  }

  italic(): void {
    this.wrapSelection('*', '*');
  }

  /** Lista con bullets — prepend "- " a cada línea de la selección. */
  bulletList(): void {
    this.transformLines((line, _i) => (line.trim() ? `- ${line.replace(/^[-•*]\s*/, '')}` : line));
  }

  /** Lista numerada — prepend "N. " a cada línea de la selección. */
  numberedList(): void {
    let counter = 1;
    this.transformLines((line) => {
      if (!line.trim()) return line;
      const cleaned = line.replace(/^(\d+\.\s+|[-•*]\s+)/, '');
      return `${counter++}. ${cleaned}`;
    });
  }

  /** Quita prefijos de lista, asteriscos de bold/italic. */
  clearFormat(): void {
    this.transformLines((line) =>
      line
        .replace(/^(\d+\.\s+|[-•*]\s+)/, '')
        .replace(/\*\*(.+?)\*\*/g, '$1')
        .replace(/(?<!\*)\*([^*\n]+)\*(?!\*)/g, '$1'),
    );
  }

  // ---- Helpers de mutación --------------------------------------

  private wrapSelection(prefix: string, suffix: string): void {
    const ta = this.activeTextarea;
    if (!ta) return;
    const start = ta.selectionStart;
    const end = ta.selectionEnd;
    const value = ta.value;
    const selected = value.slice(start, end);
    // Si no hay selección, insertamos los markers y dejamos el cursor entre ellos.
    const replacement = selected
      ? `${prefix}${selected}${suffix}`
      : `${prefix}${suffix}`;
    const before = value.slice(0, start);
    const after = value.slice(end);
    ta.value = `${before}${replacement}${after}`;
    const cursorPos = selected
      ? start + replacement.length
      : start + prefix.length;
    ta.setSelectionRange(cursorPos, cursorPos);
    this.notifyChange(ta);
    ta.focus();
  }

  /** Aplica una función a cada línea de la selección (o a la línea actual
   *  si no hay rango). Usado para listas. */
  private transformLines(fn: (line: string, index: number) => string): void {
    const ta = this.activeTextarea;
    if (!ta) return;
    const value = ta.value;
    // Expandimos la selección al inicio/fin de las líneas tocadas para
    // que aplicar "lista" a un cursor en el medio de una línea afecte la
    // línea entera, no parta el prefijo.
    const startOfLine = value.lastIndexOf('\n', ta.selectionStart - 1) + 1;
    const endOfSel = ta.selectionEnd;
    const endOfLine = value.indexOf('\n', endOfSel);
    const realEnd = endOfLine === -1 ? value.length : endOfLine;

    const block = value.slice(startOfLine, realEnd);
    const transformed = block.split('\n').map(fn).join('\n');
    ta.value = value.slice(0, startOfLine) + transformed + value.slice(realEnd);
    ta.setSelectionRange(startOfLine, startOfLine + transformed.length);
    this.notifyChange(ta);
    ta.focus();
  }

  /** Dispara un evento `input` para que Angular Forms recoja el cambio. */
  private notifyChange(ta: HTMLTextAreaElement): void {
    ta.dispatchEvent(new Event('input', { bubbles: true }));
  }
}

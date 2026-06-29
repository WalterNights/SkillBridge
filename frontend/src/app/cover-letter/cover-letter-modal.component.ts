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

import {
  CoverLetterDto,
  CoverLetterLanguage,
  CoverLetterService,
  CoverLetterTone,
} from '../services/cover-letter.service';
import { ToastService } from '../services/toast.service';

type ViewMode = 'loading' | 'empty' | 'ready' | 'generating' | 'error';

/**
 * Modal para generar / ver / editar la carta de presentación de una oferta.
 *
 * Embebido inline en /jobs/:id (no se pinta como dialog full-page para
 * que el user vea la oferta detrás como contexto).
 *
 * Flow:
 *   1. Al abrirse, llama a CoverLetterService.getForOffer() → si hay,
 *      pasa a 'ready'. Si no, 'empty' (CTA "Generar").
 *   2. User selecciona tono + idioma → click "Generar" → POST,
 *      pasa a 'ready' con el texto.
 *   3. User puede editar el textarea inline. Al hacer blur, autosave
 *      (debounced en el componente padre — acá emitimos cambios).
 *   4. Acciones: Regenerar (con warning si user_edited), Copiar,
 *      Descargar (.txt), Cerrar.
 */
@Component({
  selector: 'app-cover-letter-modal',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './cover-letter-modal.component.html',
  styleUrls: ['./cover-letter-modal.component.scss'],
})
export class CoverLetterModalComponent implements OnInit {
  @Input({ required: true }) offerId!: number;
  @Input() offerTitle = '';
  @Input() offerCompany = '';
  @Output() closed = new EventEmitter<void>();

  view = signal<ViewMode>('loading');
  letter = signal<CoverLetterDto | null>(null);
  editorContent = '';

  selectedTone: CoverLetterTone = 'cercano';
  selectedLanguage: CoverLetterLanguage = 'es';
  errorMsg = '';
  isSaving = false;

  private coverLetterService = inject(CoverLetterService);
  private toast = inject(ToastService);

  ngOnInit(): void {
    this.coverLetterService.getForOffer(this.offerId).subscribe({
      next: (letter) => {
        if (letter) {
          this.letter.set(letter);
          this.editorContent = letter.content;
          this.selectedTone = letter.tone;
          this.selectedLanguage = letter.language;
          this.view.set('ready');
        } else {
          this.view.set('empty');
        }
      },
      error: () => {
        this.errorMsg = 'No pudimos cargar tu carta. Intenta de nuevo.';
        this.view.set('error');
      },
    });
  }

  generate(): void {
    if (this.letter()?.user_edited) {
      const ok = confirm(
        'Vas a perder los cambios que hiciste a la carta anterior. ¿Continuar?',
      );
      if (!ok) return;
    }

    this.view.set('generating');
    this.errorMsg = '';
    this.coverLetterService
      .generate(this.offerId, this.selectedTone, this.selectedLanguage)
      .subscribe({
        next: (letter) => {
          this.letter.set(letter);
          this.editorContent = letter.content;
          this.view.set('ready');
        },
        error: (err) => {
          const detail = err?.error?.detail || 'No pudimos generar la carta. Intenta de nuevo.';
          this.errorMsg = detail;
          this.view.set(this.letter() ? 'ready' : 'empty');
        },
      });
  }

  /** Persiste edición manual del user. */
  saveEdits(): void {
    const letter = this.letter();
    if (!letter) return;
    if (this.editorContent === letter.content) return;

    this.isSaving = true;
    this.coverLetterService.updateContent(letter.id, this.editorContent).subscribe({
      next: (updated) => {
        this.letter.set(updated);
        this.isSaving = false;
      },
      error: () => {
        this.isSaving = false;
        this.toast.error('No pudimos guardar tus cambios');
      },
    });
  }

  copyToClipboard(): void {
    if (!this.editorContent) return;
    navigator.clipboard
      .writeText(this.editorContent)
      .then(() => this.toast.success('Carta copiada al portapapeles'))
      .catch(() => this.toast.error('No pudimos copiar la carta'));
  }

  downloadAsText(): void {
    if (!this.editorContent) return;
    const blob = new Blob([this.editorContent], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    const safeTitle = (this.offerTitle || 'oferta').replace(/[^a-z0-9]+/gi, '-').toLowerCase();
    a.download = `carta-${safeTitle}.txt`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }

  close(): void {
    this.closed.emit();
  }
}

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

import { ToastService } from '../../services/toast.service';
import {
  TwoFactorSetupResponse,
  TwoFactorService,
} from '../../services/two-factor.service';

type Mode = 'enable' | 'disable';
type ViewState = 'loading' | 'ready' | 'verifying' | 'error';

/**
 * Modal del flow de 2FA. Dos modos:
 *
 *   - `mode='enable'`: llama a setup() al montarse, muestra QR + secret
 *     en texto, pide código de 6 dígitos del authenticator app, llama
 *     activate(code). Emite `enabled=true` al éxito.
 *
 *   - `mode='disable'`: muestra UI minimal con input de código (verifica
 *     identidad), llama disable(code). Emite `enabled=false` al éxito.
 *
 * El componente padre (settings) abre el modal con el modo correcto
 * según el estado actual de 2FA.
 */
@Component({
  selector: 'app-two-factor-modal',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './two-factor-modal.component.html',
  styleUrls: ['./two-factor-modal.component.scss'],
})
export class TwoFactorModalComponent implements OnInit {
  @Input({ required: true }) mode: Mode = 'enable';
  /** Emite el nuevo estado de 2FA. Padre actualiza su signal local. */
  @Output() changed = new EventEmitter<boolean>();
  @Output() closed = new EventEmitter<void>();

  view = signal<ViewState>('loading');
  setupData = signal<TwoFactorSetupResponse | null>(null);
  code = '';
  errorMsg = '';

  private api = inject(TwoFactorService);
  private toast = inject(ToastService);

  ngOnInit(): void {
    if (this.mode === 'enable') {
      this.startSetup();
    } else {
      this.view.set('ready'); // disable no necesita setup, solo input de código
    }
  }

  startSetup(): void {
    this.view.set('loading');
    this.errorMsg = '';
    this.api.setup().subscribe({
      next: (res) => {
        this.setupData.set(res);
        this.view.set('ready');
      },
      error: (err) => {
        const detail = err?.error?.detail || 'No pudimos generar la configuración de 2FA.';
        this.errorMsg = detail;
        this.view.set('error');
      },
    });
  }

  submit(): void {
    const cleaned = this.code.replace(/\s/g, '');
    if (!/^\d{6}$/.test(cleaned)) {
      this.errorMsg = 'El código debe tener 6 dígitos.';
      return;
    }
    this.errorMsg = '';
    this.view.set('verifying');

    const op = this.mode === 'enable' ? this.api.activate(cleaned) : this.api.disable(cleaned);

    op.subscribe({
      next: (res) => {
        this.view.set('ready');
        this.changed.emit(res.enabled);
        this.toast.success(
          this.mode === 'enable'
            ? 'Verificación en dos pasos activada.'
            : 'Verificación en dos pasos desactivada.',
        );
        this.closed.emit();
      },
      error: (err) => {
        const detail = err?.error?.detail || 'Código inválido.';
        this.errorMsg = detail;
        this.view.set('ready');
      },
    });
  }

  copySecret(): void {
    const secret = this.setupData()?.secret;
    if (!secret) return;
    navigator.clipboard
      .writeText(secret)
      .then(() => this.toast.success('Secret copiado al portapapeles'))
      .catch(() => this.toast.error('No pudimos copiar el secret'));
  }

  close(): void {
    this.closed.emit();
  }
}

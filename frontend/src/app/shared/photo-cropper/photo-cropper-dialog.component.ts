import { CommonModule } from '@angular/common';
import { Component, EventEmitter, Input, OnChanges, Output, SimpleChanges } from '@angular/core';

/**
 * Cropper modal con UX estilo LinkedIn — viewport fijo y centrado,
 * la imagen se mueve y zoomea dentro. Construido sin librerías
 * externas (HTML/CSS/canvas) porque ngx-image-cropper invierte la
 * lógica: en su modelo el cropper se arrastra sobre la imagen, no
 * la imagen sobre el cropper. Acá:
 *
 *   - viewport: caja fija dimensionada por `aspectRatio`
 *   - imagen:   posición absoluta, transform translate + scale
 *   - máscara:  overlay circular o rectangular que oscurece afuera
 *   - clamp:    la imagen NUNCA puede dejar gap dentro del viewport
 *   - apply:    `canvas.drawImage` extrae la región visible y exporta
 *               blob PNG a 512px en el lado mayor
 *
 * Inputs/outputs idénticos al wrapper anterior, así el host
 * (`MyProfileComponent`) no necesita cambios.
 */
@Component({
  selector: 'app-photo-cropper-dialog',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './photo-cropper-dialog.component.html',
  styleUrl: './photo-cropper-dialog.component.scss',
})
export class PhotoCropperDialogComponent implements OnChanges {
  @Input() imageFile: File | null = null;
  @Input() aspectRatio = 1;
  @Input() roundCropper = false;
  @Input() title = 'Ajustar imagen';
  @Input() applyLabel = 'Aplicar';

  @Output() applied = new EventEmitter<Blob>();
  @Output() cancelled = new EventEmitter<void>();

  /** DataURL de la imagen leída del file. null mientras carga. */
  imageUrl: string | null = null;

  /**
   * Dimensiones del viewport calculadas según aspect ratio:
   * - Wide (banner, aspect ≥ 2): ancho fijo 380, alto = 380 / aspect.
   *   Banner 4:1 → 380×95 (preview horizontal, no un cuadradote vertical).
   * - Square/portrait (avatar): alto fijo 260, ancho = 260 * aspect.
   *   Avatar 1:1 → 260×260.
   */
  get viewportW(): number {
    return this.aspectRatio >= 2 ? 380 : 260 * this.aspectRatio;
  }
  get viewportH(): number {
    return this.aspectRatio >= 2 ? 380 / this.aspectRatio : 260;
  }

  /** Modal más ancho para banner — el viewport horizontal lo necesita. */
  get isWide(): boolean {
    return this.aspectRatio >= 2;
  }

  /** Dimensiones naturales de la imagen, llenadas en (load). */
  private imgNaturalW = 0;
  private imgNaturalH = 0;

  /** Scale base para que la imagen LLENE el viewport (cover). El zoom
   *  multiplica este factor → en scale=baseScale la imagen calza
   *  exacto sin dejar hueco. */
  private baseScale = 1;

  /** Estado de transform. zoomFactor: 1×–3× del baseScale. */
  zoomFactor = 1;
  translateX = 0;
  translateY = 0;

  isProcessing = false;

  // Estado del drag.
  private dragging = false;
  private dragStartX = 0;
  private dragStartY = 0;
  private dragOriginX = 0;
  private dragOriginY = 0;

  get scale(): number {
    return this.baseScale * this.zoomFactor;
  }

  get cssTransform(): string {
    return `translate(-50%, -50%) translate(${this.translateX}px, ${this.translateY}px) scale(${this.scale})`;
  }

  ngOnChanges(changes: SimpleChanges): void {
    if (changes['imageFile'] && this.imageFile) {
      this.resetState();
      const reader = new FileReader();
      reader.onload = (e) => {
        this.imageUrl = e.target?.result as string;
      };
      reader.readAsDataURL(this.imageFile);
    }
  }

  private resetState(): void {
    this.zoomFactor = 1;
    this.translateX = 0;
    this.translateY = 0;
    this.imgNaturalW = 0;
    this.imgNaturalH = 0;
    this.baseScale = 1;
  }

  onImageLoad(event: Event): void {
    const img = event.target as HTMLImageElement;
    this.imgNaturalW = img.naturalWidth;
    this.imgNaturalH = img.naturalHeight;
    const sx = this.viewportW / this.imgNaturalW;
    const sy = this.viewportH / this.imgNaturalH;
    this.baseScale = Math.max(sx, sy);
    this.zoomFactor = 1;
    this.translateX = 0;
    this.translateY = 0;
  }

  // ---- Zoom ---------------------------------------------------------

  onZoomChange(event: Event): void {
    this.zoomFactor = parseFloat((event.target as HTMLInputElement).value);
    this.clampTranslate();
  }

  // ---- Drag (mouse + touch) ----------------------------------------

  onDragStart(event: MouseEvent | TouchEvent): void {
    if (!this.imageUrl) return;
    const p = this.pointOf(event);
    this.dragging = true;
    this.dragStartX = p.x;
    this.dragStartY = p.y;
    this.dragOriginX = this.translateX;
    this.dragOriginY = this.translateY;
    event.preventDefault();
  }

  onDragMove(event: MouseEvent | TouchEvent): void {
    if (!this.dragging) return;
    const p = this.pointOf(event);
    this.translateX = this.dragOriginX + (p.x - this.dragStartX);
    this.translateY = this.dragOriginY + (p.y - this.dragStartY);
    this.clampTranslate();
  }

  onDragEnd(): void {
    this.dragging = false;
  }

  private pointOf(event: MouseEvent | TouchEvent): { x: number; y: number } {
    if ('touches' in event && event.touches.length > 0) {
      return { x: event.touches[0].clientX, y: event.touches[0].clientY };
    }
    const m = event as MouseEvent;
    return { x: m.clientX, y: m.clientY };
  }

  /**
   * Limita el translate para que la imagen NUNCA deje gap dentro del
   * viewport. Con baseScale (cover), max=0 en ambos ejes — solo el
   * zoom in da room para mover.
   */
  private clampTranslate(): void {
    const renderedW = this.imgNaturalW * this.scale;
    const renderedH = this.imgNaturalH * this.scale;
    const maxX = Math.max(0, (renderedW - this.viewportW) / 2);
    const maxY = Math.max(0, (renderedH - this.viewportH) / 2);
    this.translateX = Math.min(maxX, Math.max(-maxX, this.translateX));
    this.translateY = Math.min(maxY, Math.max(-maxY, this.translateY));
  }

  // ---- Apply: exportar la región visible como blob ----------------

  apply(): void {
    if (!this.imageUrl || !this.imgNaturalW) return;
    this.isProcessing = true;

    // Resolución de output adaptada al uso:
    //   - Avatar (1:1):     1024px lado → ~150KB PNG, retina-ready hasta 256px display
    //   - Banner (no 1:1):  1920px lado → cubre desktop hero a retina sin pixelarse
    // Antes era 512 fijo → banner se veía borroso al renderizarse a
    // 1200px de ancho con upscale del browser.
    const isSquare = this.aspectRatio === 1;
    const outputLong = isSquare ? 1024 : 1920;

    const canvas = document.createElement('canvas');
    if (this.aspectRatio >= 1) {
      canvas.width = outputLong;
      canvas.height = Math.round(outputLong / this.aspectRatio);
    } else {
      canvas.height = outputLong;
      canvas.width = Math.round(outputLong * this.aspectRatio);
    }
    const ctx = canvas.getContext('2d');
    if (!ctx) {
      this.isProcessing = false;
      return;
    }

    // Coordenadas en la imagen NATURAL de la región visible en el
    // viewport. La derivación es: cada píxel (cx, cy) del viewport
    // corresponde a la posición de la imagen natural
    //   sx = imgW/2 - translateX/s - viewportW/(2s) + cx/s
    //   sy = imgH/2 - translateY/s - viewportH/(2s) + cy/s
    // de donde el top-left visible (cx=cy=0) y el tamaño:
    const s = this.scale;
    const sw = this.viewportW / s;
    const sh = this.viewportH / s;
    const sx = this.imgNaturalW / 2 - this.translateX / s - sw / 2;
    const sy = this.imgNaturalH / 2 - this.translateY / s - sh / 2;

    const img = new Image();
    img.onload = () => {
      ctx.drawImage(img, sx, sy, sw, sh, 0, 0, canvas.width, canvas.height);
      // Avatar como PNG (lossless, ~150KB a 1024). Banner como JPEG
      // (a 1920px un PNG pesa varios MB y revienta el cap de 5MB del
      // backend; JPEG quality 0.92 es indistinguible visualmente).
      const mimeType = isSquare ? 'image/png' : 'image/jpeg';
      const quality = isSquare ? undefined : 0.92;
      canvas.toBlob(
        (blob) => {
          this.isProcessing = false;
          if (blob) this.applied.emit(blob);
        },
        mimeType,
        quality,
      );
    };
    img.onerror = () => {
      this.isProcessing = false;
    };
    img.src = this.imageUrl!;
  }

  cancel(): void {
    if (this.isProcessing) return;
    this.cancelled.emit();
  }
}

import { CommonModule } from '@angular/common';
import { Component, Input, computed, forwardRef, signal } from '@angular/core';
import { ControlValueAccessor, NG_VALUE_ACCESSOR } from '@angular/forms';

import { CityData } from '../../models/country.model';

/** Máximo de sugerencias en el datalist — con miles de ciudades por país
 *  (ES ~6.700, MX ~9.200) renderizarlas todas vuelve lento el móvil. */
const MAX_SUGGESTIONS = 50;

/** Minúsculas y sin tildes, para que "medellin" encuentre "Medellín". */
function normalize(text: string): string {
  return text
    .normalize('NFD')
    .replace(/\p{Diacritic}/gu, '')
    .toLowerCase()
    .trim();
}

/**
 * Campo de ciudad con sugerencias mientras se escribe.
 *
 * Reemplaza al `<select>` con todas las ciudades del país: en móvil había
 * que scrollear miles de opciones, y si la ciudad no estaba en los datos de
 * `country-state-city` (ej. Asturias tiene 0 ciudades) el usuario no podía
 * elegirla. Acá el texto es libre — las sugerencias solo ayudan.
 *
 * Uso: `<app-city-input formControlName="city" [cities]="cities" inputId="city" />`
 */
@Component({
  selector: 'app-city-input',
  standalone: true,
  imports: [CommonModule],
  providers: [
    {
      provide: NG_VALUE_ACCESSOR,
      useExisting: forwardRef(() => CityInputComponent),
      multi: true,
    },
  ],
  template: `
    <input
      [id]="inputId"
      type="text"
      class="field-input"
      autocomplete="off"
      [attr.list]="inputId + '-options'"
      [value]="query()"
      [disabled]="disabled()"
      placeholder="Escribe tu ciudad"
      (input)="onInput($event)"
      (blur)="onTouched()"
    />
    <datalist [id]="inputId + '-options'">
      <option *ngFor="let name of suggestions(); trackBy: trackByName" [value]="name"></option>
    </datalist>
  `,
})
export class CityInputComponent implements ControlValueAccessor {
  @Input({ required: true }) inputId!: string;

  @Input() set cities(value: CityData[] | null | undefined) {
    // Hay ciudades homónimas en distintas regiones — dedupe por nombre.
    const names = [...new Set((value ?? []).map((c) => c.name))];
    this.cityNames.set(names.map((name) => ({ name, key: normalize(name) })));
  }

  private cityNames = signal<{ name: string; key: string }[]>([]);
  query = signal('');
  disabled = signal(false);

  /** Primero las que empiezan con lo escrito, después las que lo contienen. */
  suggestions = computed<string[]>(() => {
    const q = normalize(this.query());
    const all = this.cityNames();
    if (!q) return all.slice(0, MAX_SUGGESTIONS).map((c) => c.name);

    const startsWith = all.filter((c) => c.key.startsWith(q));
    const contains = all.filter((c) => !c.key.startsWith(q) && c.key.includes(q));
    return [...startsWith, ...contains].slice(0, MAX_SUGGESTIONS).map((c) => c.name);
  });

  private onChange: (value: string) => void = () => {};
  onTouched: () => void = () => {};

  trackByName(_: number, name: string): string {
    return name;
  }

  onInput(event: Event): void {
    const value = (event.target as HTMLInputElement).value;
    this.query.set(value);
    this.onChange(value);
  }

  writeValue(value: string | null): void {
    this.query.set(value ?? '');
  }

  registerOnChange(fn: (value: string) => void): void {
    this.onChange = fn;
  }

  registerOnTouched(fn: () => void): void {
    this.onTouched = fn;
  }

  setDisabledState(isDisabled: boolean): void {
    this.disabled.set(isDisabled);
  }
}

import { Country } from 'country-state-city';

import { CountryData } from '../../models/country.model';

/** País de `country-state-city` + nombre visible en español. */
export interface LocalizedCountry extends CountryData {
  /** Nombre para mostrar ("España"). `name` sigue en inglés ("Spain")
   *  porque es el valor que se guarda en el perfil. */
  label: string;
}

let cache: LocalizedCountry[] | null = null;
let displayNames: Intl.DisplayNames | null | undefined;

function spanishRegionNames(): Intl.DisplayNames | null {
  if (displayNames === undefined) {
    try {
      displayNames = new Intl.DisplayNames(['es'], { type: 'region' });
    } catch {
      // Navegador sin soporte → caemos al código/nombre en inglés.
      displayNames = null;
    }
  }
  return displayNames;
}

/** Nombre en español de un código ISO ("ES" → "España"). */
export function countryLabel(isoCode: string): string {
  return spanishRegionNames()?.of(isoCode) ?? isoCode;
}

/**
 * Países con nombre en español, ordenados alfabéticamente en español.
 *
 * La librería solo trae nombres en inglés: "Spain" quedaba en la S entre
 * "Saint…"/"San…" y un usuario hispanohablante la buscaba en la E. Usamos
 * `Intl.DisplayNames` (nativo del navegador) para traducir sin agregar
 * dependencias. Solo cambia lo que se MUESTRA — `name`/`isoCode` quedan
 * igual, así los perfiles guardados y los matches por nombre no cambian.
 */
export function getLocalizedCountries(): LocalizedCountry[] {
  if (cache) return cache;

  const names = spanishRegionNames();
  cache = Country.getAllCountries()
    .map((c) => ({ ...c, label: names?.of(c.isoCode) ?? c.name }))
    .sort((a, b) => a.label.localeCompare(b.label, 'es', { sensitivity: 'base' }));
  return cache;
}

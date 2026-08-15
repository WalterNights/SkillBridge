import { Injectable, computed, signal } from '@angular/core';

import es from './es.json';
import en from './en.json';

export type PortfolioLang = 'es' | 'en';

type Dict = typeof es;

const BUNDLED_DICTS: Record<PortfolioLang, Dict> = { es, en: en as Dict };

const STORAGE_KEY = 'portfolio.lang';

/**
 * i18n mínimo scopeado al portafolio — cero dependencias externas.
 *
 * SkilTak no usa ngx-translate ni @angular/localize a nivel app, y la
 * consigna del portafolio era "no agregar integraciones nuevas". Este
 * service resuelve strings desde dos JSON estáticos (es/en) por path
 * "a.b.c" y expone la selección como signal para que los componentes
 * re-rendericen al togglear idioma.
 *
 * Persistencia: localStorage. Detección inicial: navigator.language
 * (fallback a 'es').
 */
@Injectable({ providedIn: 'root' })
export class PortfolioI18nService {
  private readonly _lang = signal<PortfolioLang>(this.detectInitial());

  /** Overrides opcionales del backend. Cuando el shell recibe el
   *  payload de /api/portfolio/<slug>/, llama `applyBackendContent()`
   *  con los diccionarios ES/EN y sobreescriben los bundled. Si el
   *  backend responde 404 o falla, quedan los bundled y el sitio no
   *  se rompe (fallback graceful). */
  private readonly _overrides = signal<Partial<Record<PortfolioLang, Dict>>>({});

  readonly lang = this._lang.asReadonly();
  readonly dict = computed<Dict>(() => {
    const lang = this._lang();
    return this._overrides()[lang] ?? BUNDLED_DICTS[lang];
  });

  /** Imágenes servidas por el backend, keyed por `project_id`. La
   *  ProjectsSection las consulta al renderizar cada card. */
  private readonly _images = signal<Record<string, { url: string; alt: string }>>({});
  readonly images = this._images.asReadonly();

  imageFor(projectId: string): { url: string; alt: string } | undefined {
    return this._images()[projectId];
  }

  /** Sobreescribe los diccionarios con contenido del backend. Merge
   *  shallow por idioma: si el backend devuelve un objeto vacío, se
   *  mantiene el bundled para ese idioma (evita blanquear todo por un
   *  seed incompleto). */
  applyBackendContent(payload: {
    es?: unknown;
    en?: unknown;
    images?: { project_id: string; url: string; alt_text: string }[];
  }): void {
    const next: Partial<Record<PortfolioLang, Dict>> = {};
    if (payload.es && typeof payload.es === 'object' && Object.keys(payload.es).length > 0) {
      next.es = payload.es as Dict;
    }
    if (payload.en && typeof payload.en === 'object' && Object.keys(payload.en).length > 0) {
      next.en = payload.en as Dict;
    }
    this._overrides.set(next);

    if (payload.images?.length) {
      // Si hay varias imágenes por project_id, gana la última del array
      // (el backend las devuelve `-created_at`, así que la última en
      // procesarse termina siendo la más vieja — invertimos para que
      // la más reciente pise).
      const idx: Record<string, { url: string; alt: string }> = {};
      for (const img of [...payload.images].reverse()) {
        idx[img.project_id] = { url: img.url, alt: img.alt_text };
      }
      this._images.set(idx);
    } else {
      this._images.set({});
    }
  }

  setLang(lang: PortfolioLang): void {
    this._lang.set(lang);
    try {
      localStorage.setItem(STORAGE_KEY, lang);
      document.documentElement.setAttribute('lang', lang);
    } catch {
      // localStorage puede fallar en modo privado — degradación silenciosa,
      // el signal sigue funcionando en memoria.
    }
  }

  toggle(): void {
    this.setLang(this._lang() === 'es' ? 'en' : 'es');
  }

  /** Traduce por dot-path. Devuelve la key si no existe (fail-loud en dev). */
  t(path: string): string {
    const value = this.resolve(path, this.dict());
    return typeof value === 'string' ? value : path;
  }

  /** Devuelve el nodo raw (útil para arrays de párrafos o items). */
  raw<T = unknown>(path: string): T {
    return this.resolve(path, this.dict()) as T;
  }

  private resolve(path: string, dict: Dict): unknown {
    return path.split('.').reduce<unknown>((acc, key) => {
      if (acc && typeof acc === 'object' && key in acc) {
        return (acc as Record<string, unknown>)[key];
      }
      return undefined;
    }, dict);
  }

  private detectInitial(): PortfolioLang {
    try {
      const stored = localStorage.getItem(STORAGE_KEY) as PortfolioLang | null;
      if (stored === 'es' || stored === 'en') return stored;
    } catch {
      // ignore
    }
    const nav = typeof navigator !== 'undefined' ? navigator.language : 'es';
    return nav.toLowerCase().startsWith('en') ? 'en' : 'es';
  }
}

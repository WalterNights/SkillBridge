/**
 * Mapeo job offer → portal de origen, para renderizar el avatar de
 * la card con el color/inicial del job board correspondiente.
 *
 * Detecta primero por URL (lo más confiable: una oferta de LinkedIn
 * apunta a linkedin.com aunque el scraper la tagueó como "websearch").
 * Fallback al campo `portal` del backend cuando la URL no calza con
 * ningún portal conocido.
 */

export type PortalKey =
  | 'linkedin'
  | 'elempleo'
  | 'bumeran'
  | 'indeed'
  | 'computrabajo'
  | 'weworkremotely'
  | 'getonbrd'
  | 'magneto'
  | 'trabajos_co'
  | 'hireline'
  | 'trabajando'
  | 'generic';

interface PortalMeta {
  key: PortalKey;
  /** Etiqueta legible (LinkedIn, Elempleo, …) para tooltip / fallback */
  label: string;
  /** Marca corta (1-2 letras) usada como contenido del avatar */
  mark: string;
}

const _PORTAL_META: Record<PortalKey, Omit<PortalMeta, 'key'>> = {
  linkedin: { label: 'LinkedIn', mark: 'in' },
  elempleo: { label: 'Elempleo', mark: 'el' },
  bumeran: { label: 'Bumeran', mark: 'B' },
  indeed: { label: 'Indeed', mark: 'I' },
  computrabajo: { label: 'Computrabajo', mark: 'CT' },
  weworkremotely: { label: 'WeWorkRemotely', mark: 'WWR' },
  getonbrd: { label: 'Get on Board', mark: 'GB' },
  magneto: { label: 'Magneto365', mark: 'M' },
  trabajos_co: { label: 'Trabajos Colombia', mark: 'TC' },
  hireline: { label: 'Hireline', mark: 'HL' },
  trabajando: { label: 'Trabajando.com', mark: 'TR' },
  generic: { label: 'Oferta', mark: '' },
};

interface OfferShape {
  url?: string;
  portal?: string;
}

export function detectPortal(offer: OfferShape | null | undefined): PortalKey {
  if (!offer) return 'generic';

  const url = (offer.url || '').toLowerCase();
  if (url.includes('linkedin.com')) return 'linkedin';
  if (url.includes('elempleo.com')) return 'elempleo';
  if (url.includes('bumeran')) return 'bumeran';
  if (url.includes('indeed')) return 'indeed';
  if (url.includes('computrabajo')) return 'computrabajo';
  if (url.includes('weworkremotely')) return 'weworkremotely';
  if (url.includes('getonbrd')) return 'getonbrd';
  if (url.includes('magneto')) return 'magneto';
  if (url.includes('trabajos.com')) return 'trabajos_co';
  if (url.includes('hireline.io')) return 'hireline';
  if (url.includes('trabajando.c')) return 'trabajando';

  // Fallback al portal del backend (por si el scraper directo nos da
  // el portal pero la URL es una variante que no matchea ningún substring).
  const p = (offer.portal || '').toLowerCase();
  if (p in _PORTAL_META && p !== 'generic') return p as PortalKey;

  return 'generic';
}

export function portalMeta(offer: OfferShape | null | undefined): PortalMeta {
  const key = detectPortal(offer);
  return { key, ...(_PORTAL_META[key] ?? _PORTAL_META.generic) };
}

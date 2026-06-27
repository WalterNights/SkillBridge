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
  | 'torre'
  // Portales creativos atendidos via WebSearch (DDG) — la oferta llega
  // tageada `portal=websearch` pero la URL apunta al dominio real.
  // Detectamos por URL para que el avatar muestre la marca correcta.
  | 'domestika'
  | 'behance'
  | 'workana'
  | 'dribbble'
  | 'freelancer'
  | 'generic';

interface PortalMeta {
  key: PortalKey;
  /** Etiqueta legible (LinkedIn, Elempleo, …) para tooltip / fallback */
  label: string;
  /** Marca corta (1-2 letras) usada como contenido del avatar */
  mark: string;
}

// Convención: `mark` debe ser 1-2 caracteres. Con 3+ se desborda el
// avatar (size fijo 32-40px) y queda visualmente roto. Si necesitás
// distinguir más de un portal con misma inicial, usá una combinación
// de 2 letras representativa (CT para Computrabajo, WW para
// WeWorkRemotely) en vez de truncar.
const _PORTAL_META: Record<PortalKey, Omit<PortalMeta, 'key'>> = {
  linkedin: { label: 'LinkedIn', mark: 'in' },
  elempleo: { label: 'Elempleo', mark: 'el' },
  bumeran: { label: 'Bumeran', mark: 'B' },
  indeed: { label: 'Indeed', mark: 'I' },
  computrabajo: { label: 'Computrabajo', mark: 'CT' },
  weworkremotely: { label: 'WeWorkRemotely', mark: 'WW' },
  getonbrd: { label: 'Get on Board', mark: 'GB' },
  magneto: { label: 'Magneto365', mark: 'M' },
  trabajos_co: { label: 'Trabajos Colombia', mark: 'TC' },
  hireline: { label: 'Hireline', mark: 'HL' },
  trabajando: { label: 'Trabajando.com', mark: 'TR' },
  torre: { label: 'Torre', mark: 'TO' },
  domestika: { label: 'Domestika', mark: 'D' },
  behance: { label: 'Behance', mark: 'Be' },
  workana: { label: 'Workana', mark: 'Wk' },
  dribbble: { label: 'Dribbble', mark: 'Dr' },
  freelancer: { label: 'Freelancer', mark: 'Fl' },
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
  // torre.ai (canónico) + torre.co (dominio viejo redirige pero algunas
  // URLs guardadas pre-migration 0011 podrían existir todavía).
  if (url.includes('torre.ai') || url.includes('torre.co')) return 'torre';
  // Portales creativos atendidos via WebSearch — la URL apunta al
  // dominio real del portal, no a `websearch`.
  if (url.includes('domestika.org')) return 'domestika';
  if (url.includes('behance.net')) return 'behance';
  if (url.includes('workana.com')) return 'workana';
  if (url.includes('dribbble.com')) return 'dribbble';
  if (url.includes('freelancer.com')) return 'freelancer';

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

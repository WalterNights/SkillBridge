/**
 * Parseo heurístico de texto libre de experiencia/educación → entries
 * estructuradas. Usado por `startStructuredExperience/Education` para
 * pre-llenar el FormArray al migrar de modo legacy.
 *
 * Formato esperado (el que genera el propio /cv al exportar y el que
 * la mayoría de users copia-pega):
 *
 *   ** Empresa (Ciudad, País) **
 *   ** Cargo [Mes Año - Mes Año] **
 *   - Bullet 1
 *   - Bullet 2
 *
 *   ** Otra Empresa ...
 *
 * Reglas de diseño:
 *  - Bloques separados por línea en blanco.
 *  - Tolerante a `**` faltantes (el user real de Walter tiene un bloque
 *    sin cierre de asteriscos — funciona igual).
 *  - Tolerante a cargo y empresa en la MISMA línea o en distintas.
 *  - Fechas ES + EN. "Presente", "Actual", "Actualidad", "Present" →
 *    is_current=true.
 *  - Nunca lanza. Si un bloque no se puede parsear, devuelve una entry
 *    con los campos que sí detectó; los required vacíos los llena el
 *    user en el form.
 *  - Si el texto entero no genera ni una entry parseable, el caller
 *    hace fallback a una entry vacía (comportamiento previo).
 */

import { EducationEntry, ExperienceEntry } from '../../models/profile.model';

/** Entry con `is_current` derivado del texto ("Presente"/"Actual"). */
export type ParsedExperience = Partial<ExperienceEntry> & { is_current?: boolean };
export type ParsedEducation = Partial<EducationEntry> & { is_current?: boolean };

const _MONTHS: Record<string, string> = {
  // Español
  enero: '01', febrero: '02', marzo: '03', abril: '04',
  mayo: '05', junio: '06', julio: '07', agosto: '08',
  septiembre: '09', setiembre: '09', octubre: '10',
  noviembre: '11', diciembre: '12',
  // Inglés
  january: '01', jan: '01', february: '02', feb: '02',
  march: '03', mar: '03', april: '04', apr: '04',
  may: '05', june: '06', jun: '06', july: '07', jul: '07',
  august: '08', aug: '08', september: '09', sept: '09', sep: '09',
  october: '10', oct: '10', november: '11', nov: '11',
  december: '12', dec: '12',
};

const _CURRENT_TOKENS = new Set([
  'presente', 'present', 'actual', 'actualidad', 'hoy', 'now', 'currently',
]);

/** Normaliza acentos + lowercase para lookup del mes / palabra clave. */
function _norm(s: string): string {
  return s
    .toLowerCase()
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '')
    .trim();
}

/** "Septiembre 2025" → "2025-09". "2025" solo → "2025-01".
 *  Devuelve "" si no puede parsear. */
function _parseDateToken(token: string): { date: string; isCurrent: boolean } {
  const normalized = _norm(token);
  if (_CURRENT_TOKENS.has(normalized)) {
    return { date: '', isCurrent: true };
  }
  // "septiembre 2025" o "sep 2025"
  const monthYear = normalized.match(/^([a-z]+)\.?\s+(\d{4})$/);
  if (monthYear) {
    const monthNum = _MONTHS[monthYear[1]];
    if (monthNum) return { date: `${monthYear[2]}-${monthNum}`, isCurrent: false };
  }
  // "2025-09" ya normalizado
  const iso = normalized.match(/^(\d{4})[-/](\d{1,2})$/);
  if (iso) {
    const mm = iso[2].padStart(2, '0');
    return { date: `${iso[1]}-${mm}`, isCurrent: false };
  }
  // "2025" solo → asumimos enero.
  const yearOnly = normalized.match(/^(\d{4})$/);
  if (yearOnly) return { date: `${yearOnly[1]}-01`, isCurrent: false };
  return { date: '', isCurrent: false };
}

/** Divide un rango "Septiembre 2025 - Presente" en start/end. */
function _parseDateRange(range: string): {
  start_date: string;
  end_date: string;
  is_current: boolean;
} {
  // Aceptamos separadores: " - ", "–", "—", " a ", " to "
  const parts = range.split(/\s+[-–—]\s+|\s+a\s+|\s+to\s+/i);
  if (parts.length < 2) {
    // Solo una fecha: la ponemos como start, sin end.
    const single = _parseDateToken(parts[0] || '');
    return {
      start_date: single.date,
      end_date: '',
      is_current: false,
    };
  }
  const start = _parseDateToken(parts[0]);
  const end = _parseDateToken(parts[1]);
  return {
    start_date: start.date,
    end_date: end.isCurrent ? '' : end.date,
    is_current: end.isCurrent,
  };
}

/** Divide "Medellín, Colombia" en city + country. Tolerante a falta de
 *  coma (asume que es la ciudad sola). */
function _parseLocation(text: string): { city?: string; country?: string } {
  const parts = text.split(',').map((s) => s.trim()).filter(Boolean);
  if (parts.length === 0) return {};
  if (parts.length === 1) return { city: parts[0] };
  // Más de 2 partes: última es país, primeras son city compuesta.
  return {
    city: parts.slice(0, -1).join(', '),
    country: parts[parts.length - 1],
  };
}

/** Extrae "texto (ubicación)" → { head, location }. Si no hay paréntesis,
 *  devuelve el texto entero como head y location vacía. */
function _splitHeadAndLocation(line: string): {
  head: string;
  city?: string;
  country?: string;
} {
  const match = line.match(/^(.+?)\s*\((.+?)\)\s*$/);
  if (!match) return { head: line.trim() };
  const loc = _parseLocation(match[2]);
  return { head: match[1].trim(), city: loc.city, country: loc.country };
}

/** Quita `**` del contenido de una línea. Tolerante a asteriscos
 *  faltantes (line entera devuelta sin cambios). */
function _stripAsterisks(line: string): string {
  return line.replace(/^\*+\s*/, '').replace(/\s*\*+$/, '').trim();
}

/** Divide el texto en bloques por línea en blanco. Filtra vacíos. */
function _splitBlocks(text: string): string[] {
  return text
    .split(/\n\s*\n/)
    .map((b) => b.trim())
    .filter((b) => b.length > 0);
}

/** Parsea un bloque de experiencia. Layouts que soporta:
 *
 *  Layout A (dos líneas separadas):
 *    **Empresa (Ciudad, País)**
 *    **Cargo [Mes Año - Mes Año]**
 *    descripción...
 *
 *  Layout B (empresa + cargo en la misma línea o adyacentes sin
 *  asteriscos internos):
 *    **Empresa (Ciudad, País)
 *    Cargo (algo opcional) [Mes Año - Mes Año]**
 *    descripción...
 */
function _parseExperienceBlock(block: string): ParsedExperience | null {
  const lines = block.split(/\r?\n/).map((l) => l.trim()).filter((l) => l.length > 0);
  if (lines.length === 0) return null;

  // Busca la línea con el rango de fechas `[...]`. Suele ser la línea
  // del cargo. Si no hay, es un bloque medio informal — devolvemos lo
  // que podamos.
  const dateLineIdx = lines.findIndex((l) => /\[[^\]]+\]/.test(l));

  let company = '';
  let city: string | undefined;
  let country: string | undefined;
  let position = '';
  let start_date = '';
  let end_date = '';
  let is_current = false;

  if (dateLineIdx >= 0) {
    const dateLine = _stripAsterisks(lines[dateLineIdx]);
    // Extraer contenido de [...] y lo que queda como position.
    const rangeMatch = dateLine.match(/^(.+?)\s*\[(.+?)\]\s*$/);
    if (rangeMatch) {
      const posRaw = rangeMatch[1];
      const range = _parseDateRange(rangeMatch[2]);
      start_date = range.start_date;
      end_date = range.end_date;
      is_current = range.is_current;
      // Position puede tener `(stack)` al final: "FullStack Developer
      // (React - Next - Nest)". Sacamos ese sufijo para el field.
      position = _splitHeadAndLocation(posRaw).head;
    }
    // Company: primera línea antes de la del cargo.
    if (dateLineIdx > 0) {
      const companyLine = _stripAsterisks(lines[0]);
      const split = _splitHeadAndLocation(companyLine);
      company = split.head;
      city = split.city;
      country = split.country;
    } else {
      // Cargo en línea 0 → no hay company detectable. Dejamos vacío.
    }
  } else {
    // Sin fechas — asumimos línea 0 es company, línea 1 es cargo (si
    // existe).
    const companyLine = _stripAsterisks(lines[0]);
    const split = _splitHeadAndLocation(companyLine);
    company = split.head;
    city = split.city;
    country = split.country;
    if (lines.length > 1) position = _stripAsterisks(lines[1]);
  }

  // Descripción: todas las líneas restantes.
  const descStart = dateLineIdx >= 0 ? dateLineIdx + 1 : (position ? 2 : 1);
  const description = lines.slice(descStart).join('\n').trim();

  // Si NADA de contenido útil, no devolvemos entry (evita crear ruido).
  if (!company && !position && !description) return null;

  const result: ParsedExperience = {
    position,
    company,
    location_city: city ?? '',
    location_country: country ?? '',
    start_date,
    end_date,
    is_current,
    description,
  };
  return result;
}

/** Similar para educación. Layout típico:
 *
 *   **Título en Institución (Ciudad, País) [Mes Año - Mes Año]**
 *
 * o con salto de línea entre título e institución.
 */
function _parseEducationBlock(block: string): ParsedEducation | null {
  const lines = block.split(/\r?\n/).map((l) => l.trim()).filter((l) => l.length > 0);
  if (lines.length === 0) return null;

  // Concatenamos todas las líneas para un lookup más flexible — educación
  // suele ser 1-2 líneas.
  const joined = _stripAsterisks(lines.join(' '));

  let title = '';
  let institution = '';
  let city: string | undefined;
  let country: string | undefined;
  let start_date = '';
  let end_date = '';
  let is_current = false;

  // Buscar fechas al final: `[Mes Año - Mes Año]`.
  const dateMatch = joined.match(/\[([^\]]+)\]\s*$/);
  let head = joined;
  if (dateMatch) {
    head = joined.slice(0, dateMatch.index).trim();
    const range = _parseDateRange(dateMatch[1]);
    start_date = range.start_date;
    end_date = range.end_date;
    is_current = range.is_current;
  }

  // Buscar location entre paréntesis al final.
  const split = _splitHeadAndLocation(head);
  city = split.city;
  country = split.country;
  const remaining = split.head;

  // Separar título de institución por " en " (ES) o " at " (EN).
  const enMatch = remaining.match(/^(.+?)\s+en\s+(.+)$/i);
  const atMatch = remaining.match(/^(.+?)\s+at\s+(.+)$/i);
  if (enMatch) {
    title = enMatch[1].trim();
    institution = enMatch[2].trim();
  } else if (atMatch) {
    title = atMatch[1].trim();
    institution = atMatch[2].trim();
  } else {
    // Sin separador claro: asumimos que todo es el título, sin institución.
    title = remaining;
  }

  if (!title && !institution && !start_date) return null;

  return {
    title,
    institution,
    location_city: city ?? '',
    location_country: country ?? '',
    start_date,
    end_date,
    is_current,
  };
}

/** Parsea el texto libre de experiencia. Devuelve entries en el orden
 *  del texto. Si no puede parsear nada, devuelve []. */
export function parseLegacyExperience(text: string | undefined | null): ParsedExperience[] {
  if (!text || !text.trim()) return [];
  const blocks = _splitBlocks(text);
  const entries: ParsedExperience[] = [];
  for (const block of blocks) {
    const parsed = _parseExperienceBlock(block);
    if (parsed) entries.push(parsed);
  }
  return entries;
}

export function parseLegacyEducation(text: string | undefined | null): ParsedEducation[] {
  if (!text || !text.trim()) return [];
  const blocks = _splitBlocks(text);
  const entries: ParsedEducation[] = [];
  for (const block of blocks) {
    const parsed = _parseEducationBlock(block);
    if (parsed) entries.push(parsed);
  }
  return entries;
}

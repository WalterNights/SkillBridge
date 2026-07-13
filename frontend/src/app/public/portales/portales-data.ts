/**
 * Catálogo de portales de empleo que SkilTak scrapea.
 *
 * Es el espejo del registry backend (`jobs.adapters.scrapers.registry`).
 * Cada vez que se agrega un scraper nuevo hay que actualizarlo acá — el
 * costo de un archivo curado es preferible a exponerlo por API porque:
 *   - Los strings user-facing (descripción, países, verticales) son más
 *     concretos que los de `scraper_cls.description` (pensados para el
 *     LLM del PortalRouterService, más técnicos).
 *   - Cambia con muy baja frecuencia (~1 portal cada varios meses).
 *
 * Cuando llegue el momento de exponerlo por API, se hace via un endpoint
 * simple GET /api/jobs/portals/ que devuelve `available_portals()` + el
 * bloque de metadatos user-facing.
 */

export interface JobPortal {
  key: string;
  name: string;
  homeUrl: string;
  /** Frase corta que resume el foco del portal, para la card. */
  summary: string;
  /** Países donde el portal tiene volumen relevante. Solo LATAM + global. */
  countries: string[];
  /** Verticales / categorías que el portal cubre bien. En castellano
   * cotidiano (no las keys internas del backend). */
  verticals: string[];
  /** Tipo del portal — clasificación visual para agrupar en la UI. */
  kind: 'generalista' | 'empresa' | 'tech' | 'remoto' | 'agregador';
}

export const JOB_PORTALS: readonly JobPortal[] = [
  {
    key: 'linkedin',
    name: 'LinkedIn',
    homeUrl: 'https://linkedin.com/jobs',
    summary:
      'Red profesional global. Cobertura amplia en todas las verticales — especialmente fuerte para roles mid-senior y multinacionales.',
    countries: ['LATAM', 'Global'],
    verticals: ['Tecnología', 'Marketing', 'Ventas', 'Finanzas', 'RRHH', 'Ejecutivo'],
    kind: 'generalista',
  },
  {
    key: 'computrabajo',
    name: 'Computrabajo',
    homeUrl: 'https://computrabajo.com',
    summary:
      'Bolsa generalista líder en LATAM. Volumen alto para oficios, atención al cliente, ventas retail, operaciones y roles junior.',
    countries: ['Colombia', 'México', 'Argentina', 'Chile', 'Perú', 'Venezuela'],
    verticals: ['Todos los sectores'],
    kind: 'generalista',
  },
  {
    key: 'indeed',
    name: 'Indeed',
    homeUrl: 'https://indeed.com',
    summary:
      'Buscador de empleo global con presencia LATAM. Agrega ofertas de miles de fuentes — bueno para descubrir vacantes que no publican en otros portales.',
    countries: ['LATAM', 'Global'],
    verticals: ['Todos los sectores'],
    kind: 'generalista',
  },
  {
    key: 'trabajos_co',
    name: 'Trabajos.co',
    homeUrl: 'https://trabajos.co',
    summary:
      'Portal específico para Colombia con foco en Bogotá, Medellín, Cali y Barranquilla. Buena cobertura de oficios y atención al público.',
    countries: ['Colombia'],
    verticals: ['Todos los sectores'],
    kind: 'generalista',
  },
  {
    key: 'magneto',
    name: 'Magneto Empleos',
    homeUrl: 'https://magneto365.com',
    summary:
      'Portal colombiano orientado a perfiles ejecutivos y profesionales. Foco en cargos administrativos, comerciales y de gestión.',
    countries: ['Colombia'],
    verticals: ['Administración', 'Ventas', 'Finanzas', 'Ejecutivo'],
    kind: 'generalista',
  },
  {
    key: 'trabajando',
    name: 'Trabajando.com',
    homeUrl: 'https://trabajando.com',
    summary:
      'Bolsa regional con presencia en varios países de LATAM. Buena cobertura para roles corporativos y perfiles técnicos.',
    countries: ['Chile', 'Argentina', 'México', 'Colombia', 'Perú'],
    verticals: ['Todos los sectores'],
    kind: 'generalista',
  },
  {
    key: 'meli',
    name: 'Mercado Libre',
    homeUrl: 'https://mercadolibre.eightfold.ai/careers',
    summary:
      'Vacantes propias de Mercado Libre — el fintech + marketplace más grande de LATAM. Proceso de selección serio y equipos multi-vertical.',
    countries: ['Argentina', 'Brasil', 'Colombia', 'México', 'Chile', 'Perú', 'Uruguay'],
    verticals: ['Tecnología', 'Producto', 'Diseño', 'Marketing', 'Ventas', 'Operaciones'],
    kind: 'empresa',
  },
  {
    key: 'torre',
    name: 'Torre',
    homeUrl: 'https://torre.ai',
    summary:
      'Bolsa moderna con foco en LATAM y remoto. Especializada en tech, producto y diseño — perfecta si buscas cultura startup.',
    countries: ['LATAM', 'Global'],
    verticals: ['Tecnología', 'Producto', 'Diseño', 'Marketing'],
    kind: 'tech',
  },
  {
    key: 'hireline',
    name: 'Hireline',
    homeUrl: 'https://hireline.io',
    summary:
      'Portal exclusivamente tech con roles en México y LATAM. Volumen medio pero calidad de vacantes alta.',
    countries: ['México', 'LATAM'],
    verticals: ['Tecnología'],
    kind: 'tech',
  },
  {
    key: 'infojobs',
    name: 'InfoJobs',
    homeUrl: 'https://www.infojobs.net',
    summary:
      'Bolsa generalista líder en España. Útil si buscas trabajo remoto internacional o quieres mudarte a España — cubre todos los sectores.',
    countries: ['España'],
    verticals: ['Todos los sectores'],
    kind: 'generalista',
  },
  {
    key: 'weworkremotely',
    name: 'We Work Remotely',
    homeUrl: 'https://weworkremotely.com',
    summary:
      'La bolsa de remoto más grande del mundo. Empresas internacionales que contratan sin importar tu país de residencia.',
    countries: ['Global (remoto)'],
    verticals: ['Tecnología', 'Diseño', 'Marketing', 'Soporte'],
    kind: 'remoto',
  },
  {
    key: 'websearch',
    name: 'Búsqueda web (Elempleo, Bumeran, GetOnBoard)',
    homeUrl: 'https://elempleo.com',
    summary:
      'Rastreamos ofertas de portales que no tienen API pública mediante búsqueda directa. Cubre Elempleo, Bumeran, GetOnBoard y otros.',
    countries: ['Colombia', 'Argentina', 'México', 'LATAM'],
    verticals: ['Todos los sectores'],
    kind: 'agregador',
  },
];

export const PORTAL_KIND_LABELS: Record<JobPortal['kind'], string> = {
  generalista: 'Generalistas LATAM',
  empresa: 'Empresas grandes',
  tech: 'Especializados en tech',
  remoto: 'Trabajo remoto',
  agregador: 'Agregadores',
};

/** Orden en el que se muestran los grupos en la UI. */
export const PORTAL_KIND_ORDER: JobPortal['kind'][] = [
  'generalista',
  'empresa',
  'tech',
  'remoto',
  'agregador',
];

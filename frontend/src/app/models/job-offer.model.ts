export interface JobOffer {
  id: number;
  title: string;
  company: string;
  location: string;
  summary: string;
  keywords: string;
  url: string;
  portal?: string;
  /** ISO 3166-1 alpha-2 derivado del location por el backend. 'XX' =
   *  desconocido. Usado por los filtros del dashboard. */
  country?: string;
  /** Modalidad detectada heurísticamente (location + summary). Usado
   *  por el filtro del dashboard. */
  modality?: 'remote' | 'hybrid' | 'onsite' | 'unknown';
  /** Rango salarial parseado del summary. Opcional: muchas ofertas
   *  no lo publican (sobre todo en LATAM). Cuando el backend lo
   *  extrae, viene como string ya formateado ("$3M - $5M COP"). */
  salary?: string;
  /** Fecha en que el scraper la guardó. Aproxima "cuándo se publicó",
   * usado para mostrar "hace N días" en el detalle. */
  created_at?: string;
  //Fields read Only
  matched_skills: string[];
  missing_skills: string[];
  match_percentage: number;
}

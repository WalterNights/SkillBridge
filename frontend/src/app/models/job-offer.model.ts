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
  /** Salario tal como aparece en la oferta ("$3.000.000 COP", "USD 2000",
   *  "Entre 2M y 3M"). Extraído por el backend con
   *  `jobs.utils.offer_attributes.extract_salary`. Vacío en la mayoría de
   *  las ofertas LATAM porque los portales no publican salario. */
  salary_text?: string;
  /** Fecha en que el scraper la guardó. Aproxima "cuándo se publicó",
   * usado para mostrar "hace N días" en el detalle. */
  created_at?: string;
  //Fields read Only
  matched_skills: string[];
  missing_skills: string[];
  match_percentage: number;
}

export interface JobOffer {
  id: number;
  title: string;
  company: string;
  location: string;
  summary: string;
  keywords: string;
  url: string;
  portal?: string;
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

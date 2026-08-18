/**
 * Resume analysis response from backend
 */
export interface ResumeAnalysisData {
  first_name: string;
  last_name: string;
  email?: string;
  number_id?: string;
  phone_code: string;
  phone_number: string;
  country?: string;
  city?: string;
  professional_title: string;
  summary: string;
  education?: EducationEntry[] | string;
  experience?: ExperienceEntry[] | string;
  skills: string;
  linkedin_url?: string;
  portfolio_url?: string;
}

/**
 * Education entry interface.
 * `location_city` / `location_country` son opcionales porque muchos
 * perfiles no especifican lugar de estudio.
 */
export interface EducationEntry {
  title: string;
  institution: string;
  location_city?: string;
  location_country?: string;
  start_date: string;
  end_date: string;
}

/**
 * Experience entry interface.
 * `location_city` / `location_country` son opcionales — algunos jobs
 * (especialmente remotos) no traen lugar definido.
 */
export interface ExperienceEntry {
  position: string;
  company: string;
  location_city?: string;
  location_country?: string;
  start_date: string;
  end_date: string;
  description: string;
}

/**
 * Idioma que habla el usuario, con su nivel.
 * El backend lo guarda como JSON-string en un TextField, pero el
 * frontend siempre opera sobre el array parseado.
 */
export interface LanguageEntry {
  language: string;
  level: string;
}

/** Idioma activo del CV — determina qué campo (`summary` vs `summary_en`)
 *  edita el user y qué contenido se renderiza en el preview y el PDF. */
export type CvLanguage = 'es' | 'en';

/** Alineación de las descripciones en el CV renderizado. Global,
 *  no por bloque — mantener simple. */
export type CvTextAlign = 'left' | 'justify';

/** Escala del CV renderizado. Cada opción multiplica el rem base del
 *  render (ver ats-cv.component.scss). */
export type CvFontSize = 'sm' | 'md' | 'lg';

/**
 * Forma del profile tal como vive en el componente del CV ATS — post
 * normalización (`formatProfileData`). Es lo que consumen los templates
 * y el algoritmo de paginación.
 *
 * - `experience` / `education`: array si está estructurado (Gemini wizard,
 *   data nueva), string markdown si es texto libre (perfiles legacy o
 *   manual). El renderer cubre ambos casos.
 * - `languages`: SIEMPRE array tras la normalización (vacío si no hay).
 * - `*_en`: versión inglesa paralela. Si el user nunca activó EN, vienen
 *   vacíos y el editor los muestra vacíos con la opción de "copiar del
 *   español" para arrancar.
 */
export interface CvProfileData {
  id: number | null;
  first_name: string;
  last_name: string;
  email: string;
  number_id: string;
  phone_code: string;
  phone_number: string;
  city: string;
  country: string;
  location_note: string;
  professional_title: string;
  summary: string;
  linkedin_url: string;
  portfolio_url: string;
  github_url: string;
  // Skills rich text para display en el CV (separado de `skills` que
  // se usa para matching contra ofertas).
  cv_skills: string;
  cv_skills_en: string;
  skills: string;
  soft_skills: string;
  languages: LanguageEntry[];
  experience: ExperienceEntry[] | string;
  education: EducationEntry[] | string;
  // Versiones en inglés — paralelas al ES existente.
  summary_en: string;
  skills_en: string;
  soft_skills_en: string;
  experience_en: ExperienceEntry[] | string;
  education_en: EducationEntry[] | string;
  // Preferencias de display del CV.
  cv_active_language: CvLanguage;
  cv_text_align: CvTextAlign;
  cv_font_size: CvFontSize;
}

/**
 * Respuesta cruda del endpoint GET /users/profiles/ antes de normalizar.
 * Todos los campos son opcionales porque el backend puede omitir o
 * mandar null en cualquiera; `formatProfileData` se encarga de los
 * defaults antes de pasarlo al template.
 *
 * `user.email`: el backend a veces anida el email dentro del user
 * relacionado (queryset con select_related), a veces lo trae plano —
 * el formatter cubre los dos casos.
 */
export interface ProfileApiResponse {
  id?: number | null;
  first_name?: string | null;
  last_name?: string | null;
  email?: string | null;
  user?: { email?: string | null } | null;
  number_id?: string | null;
  phone_code?: string | null;
  phone_number?: string | null;
  phone?: string | null; // alias legacy
  city?: string | null;
  country?: string | null;
  location_note?: string | null;
  professional_title?: string | null;
  summary?: string | null;
  linkedin_url?: string | null;
  portfolio_url?: string | null;
  github_url?: string | null;
  cv_skills?: string | null;
  cv_skills_en?: string | null;
  skills?: string | null;
  soft_skills?: string | null;
  languages?: LanguageEntry[] | string | null;
  experience?: ExperienceEntry[] | string | null;
  education?: EducationEntry[] | string | null;
  // Versiones en inglés — todas opcionales para no romper con perfiles
  // pre-migración que no tienen estos campos en la respuesta.
  summary_en?: string | null;
  skills_en?: string | null;
  soft_skills_en?: string | null;
  experience_en?: ExperienceEntry[] | string | null;
  education_en?: EducationEntry[] | string | null;
  cv_active_language?: CvLanguage | null;
  cv_text_align?: CvTextAlign | null;
  cv_font_size?: CvFontSize | null;
}

/**
 * Envelope posible que devuelve GET /users/profiles/. DRF pagina por
 * default (`{count, results}`) pero algunos endpoints devuelven array
 * crudo o objeto singular — cubrimos los tres en el normalizer.
 */
export type ProfileApiPayload =
  | ProfileApiResponse
  | ProfileApiResponse[]
  | { results: ProfileApiResponse[] };

/**
 * Profile form data interface
 */
export interface ProfileFormData {
  first_name: string;
  last_name: string;
  email?: string;
  number_id: string;
  phone_code: string;
  phone_number: string;
  country: string;
  city: string;
  location_note?: string;
  professional_title: string;
  summary: string;
  education: EducationEntry[] | string;
  experience: ExperienceEntry[] | string;
  skills: string;
  linkedin_url: string;
  portfolio_url?: string;
  github_url?: string;
  cv_skills?: string;
  cv_skills_en?: string;
  languages?: LanguageEntry[] | string;
  resume?: File | null;
}

/**
 * Resume analysis response from backend
 */
export interface ResumeAnalysisData {
  first_name: string;
  last_name: string;
  number_id?: string;
  phone_code: string;
  phone_number: string;
  country?: string;
  city?: string;
  professional_title: string;
  summary: string;
  education?: string;
  experience?: string;
  skills: string;
  linkedin_url?: string;
  portfolio_url?: string;
}

/**
 * Education entry interface
 */
export interface EducationEntry {
  title: string;
  institution: string;
  location_city: string;
  location_country: string;
  start_date: string;
  end_date: string;
}

/**
 * Experience entry interface
 */
export interface ExperienceEntry {
  position: string;
  company: string;
  location_city: string;
  location_country: string;
  start_date: string;
  end_date: string;
  description: string;
}

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
  professional_title: string;
  summary: string;
  education: EducationEntry[] | string;
  experience: ExperienceEntry[] | string;
  skills: string;
  linkedin_url: string;
  portfolio_url?: string;
  resume?: File | null;
}

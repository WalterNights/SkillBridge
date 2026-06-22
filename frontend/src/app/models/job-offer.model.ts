export interface JobOffer {
  id: number;
  title: string;
  company: string;
  location: string;
  summary: string;
  keywords: string;
  url: string;
  portal?: string;
  //Fields read Only
  matched_skills: string[];
  missing_skills: string[];
  match_percentage: number;
}

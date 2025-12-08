/**
 * Country data interface
 */
export interface CountryData {
  name: string;
  isoCode: string;
  phonecode: string;
  flag?: string;
  currency?: string;
  latitude?: string;
  longitude?: string;
}

/**
 * City data interface
 */
export interface CityData {
  name: string;
  countryCode: string;
  stateCode?: string;
  latitude?: string;
  longitude?: string;
}

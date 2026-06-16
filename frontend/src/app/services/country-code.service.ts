import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable, shareReplay } from 'rxjs';

import { CountryCode } from '../models/country-code.model';

/**
 * Sirve el catálogo de country codes desde `assets/data/country-code.json`.
 *
 * Es un asset estático: lo cacheamos en memoria con `shareReplay(1)` para
 * que cada componente que lo pida no dispare un fetch nuevo durante la sesión.
 */
@Injectable({ providedIn: 'root' })
export class CountryCodeService {
  private codes$?: Observable<CountryCode[]>;

  constructor(private http: HttpClient) {}

  getCountryCodes(): Observable<CountryCode[]> {
    if (!this.codes$) {
      this.codes$ = this.http
        .get<CountryCode[]>('assets/data/country-code.json')
        .pipe(shareReplay(1));
    }
    return this.codes$;
  }
}

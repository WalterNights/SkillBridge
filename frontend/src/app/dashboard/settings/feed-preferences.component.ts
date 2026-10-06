import { CommonModule } from '@angular/common';
import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { forkJoin } from 'rxjs';

import { FeedPreferences, JobService } from '../../services/job.service';
import { ToastService } from '../../services/toast.service';
import { countryLabel } from '../../shared/location/countries';

type Modality = FeedPreferences['modalities_first'][number];
/** Estado de un país en las preferencias: normal, primero o al final. */
type CountryState = 'neutral' | 'first' | 'last';

const MODALITY_OPTIONS: readonly { value: Modality; label: string; icon: string }[] = [
  { value: 'remote', label: 'Remoto', icon: 'home_work' },
  { value: 'hybrid', label: 'Híbrido', icon: 'sync_alt' },
  { value: 'onsite', label: 'Presencial', icon: 'apartment' },
];

const STATE_LABEL: Record<CountryState, string> = {
  neutral: 'orden normal',
  first: 'se muestra primero',
  last: 'se muestra al final',
};

/** Orden del ciclo al hacer click en un país. */
const NEXT_STATE: Record<CountryState, CountryState> = {
  neutral: 'first',
  first: 'last',
  last: 'neutral',
};

interface CountryChip {
  iso: string;
  label: string;
  count: number;
}

/**
 * Tarjeta de /settings para las preferencias persistentes del feed.
 *
 * A diferencia de los filtros del dashboard, estas preferencias se guardan
 * en el perfil y solo REORDENAN el feed: lo preferido aparece primero y lo
 * relegado al final, sin esconder ofertas. Los países salen de
 * `filter-options` (los que de verdad tienen ofertas), con su conteo.
 */
@Component({
  selector: 'app-feed-preferences',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './feed-preferences.component.html',
})
export class FeedPreferencesComponent implements OnInit {
  private jobs = inject(JobService);
  private toast = inject(ToastService);

  readonly modalityOptions = MODALITY_OPTIONS;

  isLoading = signal(true);
  isSaving = signal(false);
  loadError = signal(false);

  modalitiesFirst = signal<Set<Modality>>(new Set());
  countryStates = signal<Record<string, CountryState>>({});
  countries = signal<CountryChip[]>([]);

  firstCountries = computed(() => this.isoCodesIn('first'));
  lastCountries = computed(() => this.isoCodesIn('last'));

  ngOnInit(): void {
    forkJoin({
      prefs: this.jobs.getFeedPreferences(),
      options: this.jobs.getFilterOptions(),
    }).subscribe({
      next: ({ prefs, options }) => {
        this.modalitiesFirst.set(new Set(prefs.modalities_first));
        const states: Record<string, CountryState> = {};
        prefs.countries_first.forEach((iso) => (states[iso] = 'first'));
        prefs.countries_last.forEach((iso) => (states[iso] = 'last'));
        this.countryStates.set(states);

        // Países con ofertas + los ya guardados aunque hoy no tengan ofertas.
        const chips = options.countries.map((c) => ({
          iso: c.value,
          label: countryLabel(c.value),
          count: c.count,
        }));
        const known = new Set(chips.map((c) => c.iso));
        Object.keys(states)
          .filter((iso) => !known.has(iso))
          .forEach((iso) => chips.push({ iso, label: countryLabel(iso), count: 0 }));
        this.countries.set(chips);
        this.isLoading.set(false);
      },
      error: () => {
        this.loadError.set(true);
        this.isLoading.set(false);
      },
    });
  }

  isModalityFirst(value: Modality): boolean {
    return this.modalitiesFirst().has(value);
  }

  toggleModality(value: Modality): void {
    this.modalitiesFirst.update((current) => {
      const next = new Set(current);
      if (!next.delete(value)) next.add(value);
      return next;
    });
  }

  countryState(iso: string): CountryState {
    return this.countryStates()[iso] ?? 'neutral';
  }

  countryAriaLabel(chip: CountryChip): string {
    return `${chip.label}: ${STATE_LABEL[this.countryState(chip.iso)]}`;
  }

  cycleCountry(iso: string): void {
    this.countryStates.update((states) => ({
      ...states,
      [iso]: NEXT_STATE[states[iso] ?? 'neutral'],
    }));
  }

  save(): void {
    this.isSaving.set(true);
    this.jobs
      .saveFeedPreferences({
        modalities_first: [...this.modalitiesFirst()],
        countries_first: this.firstCountries(),
        countries_last: this.lastCountries(),
      })
      .subscribe({
        next: () => {
          this.isSaving.set(false);
          this.toast.success('Preferencias del feed guardadas');
        },
        error: () => {
          this.isSaving.set(false);
          this.toast.error('No pudimos guardar tus preferencias.');
        },
      });
  }

  private isoCodesIn(state: CountryState): string[] {
    return Object.entries(this.countryStates())
      .filter(([, s]) => s === state)
      .map(([iso]) => iso);
  }
}

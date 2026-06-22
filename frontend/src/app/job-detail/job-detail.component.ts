import { CommonModule, Location } from '@angular/common';
import { Component, OnInit, inject } from '@angular/core';
import { Title } from '@angular/platform-browser';
import { JobService } from '../services/job.service';
import { JobOffer } from '../models/job-offer.model';
import { ActivatedRoute, Router, RouterModule } from '@angular/router';
import { portalMeta } from '../shared/portal';

/**
 * Detalle de una oferta de trabajo (/jobs/:id).
 *
 * Renderiza dentro del AppShell, así que no monta header/sidebar
 * propio. La fuente única de datos es `job` (el backend devuelve la
 * oferta enriquecida con `match_percentage`, `matched_skills` y
 * `missing_skills` via `_enrich_with_user_match`), así no dependemos
 * del cache de selección en sesión.
 */
@Component({
  selector: 'app-job-detail',
  imports: [CommonModule, RouterModule],
  standalone: true,
  templateUrl: './job-detail.component.html',
  styleUrls: ['./job-detail.component.scss'],
})
export class JobDetailComponent implements OnInit {
  job: JobOffer | null = null;
  isLoading = true;
  errorMessage = '';

  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private location = inject(Location);
  private jobService = inject(JobService);
  private titleService = inject(Title);

  constructor() {
    this.titleService.setTitle('SkilTak — Detalle de oferta');
  }

  ngOnInit() {
    const jobId = this.route.snapshot.paramMap.get('id');
    if (!jobId) {
      this.errorMessage = 'No se encontró el identificador de la oferta.';
      this.isLoading = false;
      return;
    }
    this.jobService.getJobDetail(jobId).subscribe({
      next: (data) => {
        this.job = data;
        this.isLoading = false;
      },
      error: () => {
        this.errorMessage = 'No pudimos cargar la oferta.';
        this.isLoading = false;
      },
    });
  }

  goBack(): void {
    this.location.back();
  }

  /**
   * Tier visual del match. Empareja con los dots/borders del feed
   * en /dashboard para que el usuario reconozca el ranking de
   * inmediato sin tener que leer el número.
   */
  matchTier(): 'excellent' | 'good' | 'regular' | 'low' {
    const m = this.job?.match_percentage ?? 0;
    if (m >= 100) return 'excellent';
    if (m >= 70) return 'good';
    if (m >= 50) return 'regular';
    return 'low';
  }

  /** Lista de keywords como array para renderizar como pills. */
  keywordChips(): string[] {
    if (!this.job?.keywords) return [];
    return this.job.keywords
      .split(',')
      .map((k) => k.trim())
      .filter(Boolean);
  }

  /** Portal de origen (LinkedIn, Elempleo, …) para el avatar del header. */
  portalMeta() {
    return portalMeta(this.job);
  }
}

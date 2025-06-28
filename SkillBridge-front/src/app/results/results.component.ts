import { Router } from '@angular/router';
import { CommonModule } from '@angular/common';
import { Component, OnInit } from '@angular/core';
import { Title } from '@angular/platform-browser';
import { JobOffer } from '../models/job-offer.model';
import { JobService } from '../services/job.service';

@Component({
  selector: 'app-results',
  imports: [CommonModule],
  standalone: true,
  templateUrl: './results.component.html',
  styleUrls: ['./results.component.scss']
})
export class ResultsComponent {
  offers: JobOffer[] = [];
  constructor(
    private jobService: JobService, 
    private router: Router,
    private titleService: Title
  ) {
    this.titleService.setTitle('SkillBridge - Resultados de Búsqueda');
  }
  ngOnInit(): void {
    this.offers = this.jobService.getOffers();
    if (this.offers.length === 0) {
      this.router.navigate(['/']);
    }
  }
  goToLinkedin(link: string): void {
    window.open(link, '_blank');
  }
}

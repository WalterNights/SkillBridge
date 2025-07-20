import { CommonModule } from '@angular/common';
import { Component, OnInit } from '@angular/core';
import { Title } from '@angular/platform-browser';
import { HttpClient } from '@angular/common/http';
import { JobOffer } from '../models/job-offer.model';
import { JobService } from '../services/job.service';
import { Router, RouterModule } from '@angular/router';

@Component({
  selector: 'app-results',
  imports: [CommonModule, RouterModule],
  standalone: true,
  templateUrl: './results.component.html',
  styleUrls: ['./results.component.scss']
})

export class ResultsComponent {
  offers: JobOffer[] = [];
  constructor(
    private router: Router,
    private jobService: JobService,
    private titleService: Title,
    private http: HttpClient
  ) {
    this.titleService.setTitle('SkillBridge - Resultados de Búsqueda');
  }

  ngOnInit(): void {
    this.http.get<any>('http://localhost:8000/api/jobs/jobs-offer/').subscribe({
      next: (data) => {
        this.offers = Array.isArray(data) ? data : []
      }
    })
  }

  goToDetail(job: JobOffer) {
    this.jobService.setSelectedJob(job);
    this.router.navigate(['/jobs', job.id]);
  }

  goToLinkedin(link: string): void {
    window.open(link, '_blank');
  }
}

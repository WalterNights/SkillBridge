import { Router } from '@angular/router';
import { CommonModule } from '@angular/common';
import { Component, OnInit } from '@angular/core';
import { Title } from '@angular/platform-browser';
import { HttpClient } from '@angular/common/http';
import { JobOffer } from '../models/job-offer.model';

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
    private router: Router,
    private titleService: Title,
    private http: HttpClient
  ) {
    this.titleService.setTitle('SkillBridge - Resultados de Búsqueda');
  }

  ngOnInit(): void {
    this.http.get<any>('http://localhost:8000/api/jobs/jobs-offer/').subscribe({
      next: (data) => {
        console.log(data)
        this.offers = Array.isArray(data) ? data : []
      }
    })
  }

  goToLinkedin(link: string): void {
    window.open(link, '_blank');
  }
}

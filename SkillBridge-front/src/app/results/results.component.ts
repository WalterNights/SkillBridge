import { Component} from '@angular/core';
import { CommonModule } from '@angular/common';
import { Title } from '@angular/platform-browser';
import { HttpClient } from '@angular/common/http';
import { JobOffer } from '../models/job-offer.model';
import { JobService } from '../services/job.service';
import { Router, RouterModule } from '@angular/router';
import { HTMLChangesComponent } from '../shared/html-changes/html-changes';


@Component({
  selector: 'app-results',
  imports: [CommonModule, RouterModule],
  standalone: true,
  templateUrl: './results.component.html',
  styleUrls: ['./results.component.scss']
})

export class ResultsComponent {
  offers: JobOffer[] = [];
  hoverState: { [offerId: number]: boolean } = {}
  selectedFilter: 'all' | 'good' | 'regular' | 'bad' = 'all';

  constructor(
    private router: Router,
    private jobService: JobService,
    private titleService: Title,
    private http: HttpClient,
    private changes: HTMLChangesComponent
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

  get filteredOffer() {
    if (this.selectedFilter === 'all') {
      return this.offers;
    }
    if (this.selectedFilter === 'good') {
      return this.offers.filter(offer => offer.match_percentage == 100);
    }
    if (this.selectedFilter === 'regular') {
      return this.offers.filter(offer => offer.match_percentage >= 70 && offer.match_percentage < 100);
    }
    if (this.selectedFilter === 'bad') {
      return this.offers.filter(offer => offer.match_percentage >= 50 && offer.match_percentage < 70);
    }
    return this.offers;
  }

  setFilter(filter: 'all' | 'good' | 'regular' | 'bad') {
    this.selectedFilter = filter;
  }

  goToDetail(job: JobOffer) {
    this.jobService.setSelectedJob(job);
    this.router.navigate(['/jobs', job.id]);
  }

  onHover(state: boolean, offerId: number) {
    this.hoverState[offerId] = state;
  }

  isHovered(offerId: number): boolean {
    return this.hoverState[offerId] || false;
  }

  setColor(match: number): string {
    return  this.changes.getColor(match)
  }

  setGradient(match: number, hovered: boolean): string {
    return this.changes.getGradient(match, hovered)
  }

  setWidth(hovered: boolean): string {
    return this.changes.getWidth(hovered)
  }




  obtainOffers() {
    this.jobService.getScrapedOffers().subscribe({
      next: (res: JobOffer[]) => {
        this.jobService.setOffers(res);
      },
      error: (err) => {
        console.error("❌ Error al obtener vacantes:", err);
      }
    });
  }


}

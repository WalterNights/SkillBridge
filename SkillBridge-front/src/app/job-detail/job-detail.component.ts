import { CommonModule } from '@angular/common';
import { Component, OnInit } from '@angular/core';
import { Title } from '@angular/platform-browser';
import { HttpClient } from '@angular/common/http';
import { AuthService } from '../auth/auth.service';
import { JobService } from '../services/job.service';
import { JobOffer } from '../models/job-offer.model';
import { Router, ActivatedRoute } from '@angular/router';

@Component({
  selector: 'app-job-detail',
  imports: [CommonModule],
  standalone: true,
  templateUrl: './job-detail.component.html',
  styleUrls: ['./job-detail.component.scss']
})
export class JobDetailComponent implements OnInit {
  job!: any;
  jobDetail!: JobOffer;

  constructor(
    private router: Router,
    private route: ActivatedRoute,
    private jobService: JobService,
    private authService: AuthService,
    private titleService: Title,
    private http: HttpClient
  ) {
    this.titleService.setTitle('SkillBridge - Oferta- Detalles');
  }

  ngOnInit() {
    const jobFiltered = this.jobService.getSelectedJob();
    if (jobFiltered) this.jobDetail = jobFiltered;
    const jobId = this.route.snapshot.paramMap.get('id');
    this.http.get(`http://localhost:8000/api/jobs/jobs-details/${jobId}/`).subscribe({
      next: data => this.job = data,
      error: err => console.log('Error al cargar la oferta')
    });
  }

  goToResults() {
    if (!this.authService.isAuthenticated()){
      sessionStorage.setItem('redirect_after_login', '/results');
      this.router.navigate(['/auth/login']);
    } else {
      this.router.navigate(['/results']);
    }
  }
}

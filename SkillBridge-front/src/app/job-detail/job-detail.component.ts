import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Title } from '@angular/platform-browser';
import { HttpClient } from '@angular/common/http';
import { JobService } from '../services/job.service';
import { Router, ActivatedRoute } from '@angular/router';
import { JobOffer } from '../models/job-offer.model';

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
    private route: ActivatedRoute,
    private jobService: JobService,
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
      error: err => console.log('Error al cargar la oferta', err)
    });
  }

}

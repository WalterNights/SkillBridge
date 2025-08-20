import { Router } from '@angular/router';
import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { environment } from '../../environment/environment';

@Component({
  selector: 'app-dashboard',
  imports: [CommonModule],
  standalone: true,
  templateUrl: './dashboard.component.html',
  styleUrls: ['./dashboard.component.scss']
})
export class DashboardComponent {
  users: any;

  constructor(
    private router: Router,
    private http: HttpClient,
  ){}

  ngOnInit(): void {
    this.http.get<any>(`${environment.apiUrl}/dashboard/`).subscribe({
      next: (data) => {
        this.users = data;
      }
    })
  }
}

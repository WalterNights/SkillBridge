import { Component } from '@angular/core';
import { AuthService } from '../auth.service';
import { CommonModule } from '@angular/common';
import { Title } from '@angular/platform-browser';
import { Router, RouterModule } from '@angular/router';
import { StorageMethodComponent } from '../../shared/storage-method/storage-method'; 
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';

@Component({
  selector: 'app-login',
  imports: [CommonModule, ReactiveFormsModule, RouterModule],
  standalone: true,
  templateUrl: './login.component.html',
  styleUrls: ['./login.component.scss']
})

export class LoginComponent {
  loginForm: FormGroup;
  isLoading = false;
  errorMessage = '';
  isStorage = false;
  storage: 'session' | 'local' = 'session';

  constructor(
    private fb: FormBuilder, 
    private authService: AuthService, 
    private router: Router,
    private titleService: Title,
    private storageMethod: StorageMethodComponent
  ) {
    this.titleService.setTitle('SkillBridge - Login');
    this.loginForm = this.fb.group({
      username: ['', Validators.required],
      password: ['', Validators.required]
    });
  }

  ngOnInit(){
    if(localStorage.getItem('storage') === 'true') {
      this.isStorage = true;
      this.storage = 'local';
    }
  }

  toggleStorage() {
      this.isStorage = !this.isStorage;
      if (this.isStorage) {
         localStorage.setItem('storage', 'true');
         this.storage = 'local';
      } else {
         localStorage.setItem('storage', 'false');
         this.storage = 'session';
      }
   }

  onSubmit() {
    if (this.loginForm.invalid) return;
    this.isLoading = true;
    this.authService.login(this.loginForm.value).subscribe({
      next: () => {
        setTimeout(() => {
          this.isLoading = false;
          const redirectPath = sessionStorage.getItem('redirect_after_login') || '';
          sessionStorage.removeItem('redirect_after_login');
          if(this.storageMethod.getStorageItem(this.storage, 'is_profile_complete') === 'true') {
            this.router.navigate(['/results']);
          } else {
            this.router.navigate([redirectPath]);
          }
        }, 1200);
      },
      error: () => {
        this.isLoading = false;
        this.errorMessage = 'Credenciales inválidas. Intentalo nievamente.';
      }
    });
  }
}
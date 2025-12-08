import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ReactiveFormsModule } from '@angular/forms';
import { AuthRoutingModule } from './auth-routing.module';
import { RegisterComponent } from './register/register.component';

@NgModule({
  declarations: [],
  imports: [
    CommonModule,
    RegisterComponent,
    AuthRoutingModule,
    ReactiveFormsModule
  ]
})
export class AuthModule { }

import { ComponentFixture, TestBed } from '@angular/core/testing';

import { AtsCvComponent } from './ats-cv.component';

describe('AtsCvComponent', () => {
  let component: AtsCvComponent;
  let fixture: ComponentFixture<AtsCvComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [AtsCvComponent]
    })
    .compileComponents();

    fixture = TestBed.createComponent(AtsCvComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});

import { ComponentFixture, TestBed } from '@angular/core/testing';

import { ManualProfileComponent } from './manual-profile.component';

describe('ManualProfileComponent', () => {
  let component: ManualProfileComponent;
  let fixture: ComponentFixture<ManualProfileComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ManualProfileComponent]
    })
    .compileComponents();

    fixture = TestBed.createComponent(ManualProfileComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});

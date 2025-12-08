import { Route } from '@angular/router';
import { CommonModule } from '@angular/common';
import { Component, OnDestroy, OnInit } from '@angular/core';

@Component({
  selector: 'app-loader-modal',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './loader-modal.component.html',
  styleUrls: ['./loader-modal.component.scss']
})
export class LoaderModalComponent {
  motivationalPhrases = [
    '🔍 Analizando tu perfil...',
    '📡 Buscando oportunidades relevantes para ti...',
    '🌱 Nuestro objetivo: ayudarte a crecer profesionalmente.',
    '🚀 SkilTak conecta tu talento con la vacante ideal.',
    '🎯 Esto solo es el comienzo de tu próxima etapa laboral.',
  ];
  currentPhrase = this.motivationalPhrases[0];
  pharaseIndex = 0;
  intervalId: any;
  ngOnInit() {
    this.intervalId = setInterval(() => {
      this.pharaseIndex = (this.pharaseIndex + 1) % this.motivationalPhrases.length;
      this.currentPhrase = this.motivationalPhrases[this.pharaseIndex];
    }, 3000);
  }
  ngDestroy() {
    clearInterval(this.intervalId);
  }
}

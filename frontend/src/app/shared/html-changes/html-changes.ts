import { Injectable } from "@angular/core";

@Injectable({ providedIn: 'root' })
export class HTMLChangesComponent {

  getColor(match: number): string {
    let color = '#f97315'; // orange-500
    if (match === 100) {
      color = '#22c55e'; // green-500
    } else if (match >= 70 && match < 100) {
      color = '#3b82f6'; // blue-500
    } else if (match >= 50 && match < 70) {
      color = '#f97315'; // orange-500
    }
    return color;
  }

  getGradient(match: number, hovered: boolean): string {
    const color = this.getColor(match);
    let gradient = ""
    if (hovered) {
      gradient = `conic-gradient(from 180deg at 50% 50%, ${color} 0deg, ${color} 120deg, transparent 1turn`;
    }
    return gradient;
  }

  getWidth(hovered: boolean): string {
    let width = ""
    if (hovered) {
      width = "99.5%"
    }
    return width;
  }
}
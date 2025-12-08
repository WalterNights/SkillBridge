import { Injectable } from "@angular/core";
import { MATCH_THRESHOLDS, MATCH_COLORS, UI_CONSTANTS } from '../../constants/match-thresholds';

/**
 * Service for generating dynamic HTML styles based on match percentages
 */
@Injectable({ providedIn: 'root' })
export class HTMLChangesComponent {

  /**
   * Returns color based on match percentage
   * @param match - Match percentage (0-100)
   * @returns Hex color string
   */
  getColor(match: number): string {
    if (match === MATCH_THRESHOLDS.EXCELLENT) {
      return MATCH_COLORS.EXCELLENT;
    }
    if (match >= MATCH_THRESHOLDS.GOOD_MIN && match <= MATCH_THRESHOLDS.GOOD_MAX) {
      return MATCH_COLORS.GOOD;
    }
    if (match >= MATCH_THRESHOLDS.REGULAR_MIN && match <= MATCH_THRESHOLDS.REGULAR_MAX) {
      return MATCH_COLORS.REGULAR;
    }
    return MATCH_COLORS.DEFAULT;
  }

  /**
   * Generates conic gradient for hovered state
   * @param match - Match percentage
   * @param hovered - Whether element is hovered
   * @returns CSS gradient string or empty string
   */
  getGradient(match: number, hovered: boolean): string {
    if (!hovered) return '';
    
    const color = this.getColor(match);
    return `conic-gradient(from ${UI_CONSTANTS.GRADIENT_ANGLE}deg at 50% 50%, ${color} 0deg, ${color} ${UI_CONSTANTS.GRADIENT_END_ANGLE}deg, transparent 1turn)`;
  }

  /**
   * Returns width based on hover state
   * @param hovered - Whether element is hovered
   * @returns CSS width string or empty string
   */
  getWidth(hovered: boolean): string {
    return hovered ? UI_CONSTANTS.HOVER_WIDTH : '';
  }
}
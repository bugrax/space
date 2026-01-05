/**
 * Utility functions for dashboard operations
 */

/**
 * Verdict result returned by getVerdict function
 */
export interface Verdict {
  /** Display text for the verdict (e.g., "STRONG BUILD", "SKIP") */
  text: string;
  /** Color code for the verdict badge */
  color: string;
}

/**
 * Determines the verdict/recommendation for a SaaS idea based on its score
 *
 * Score ranges:
 * - >= 75: STRONG BUILD (green)
 * - >= 50: EXPLORING (blue)
 * - >= 30: CAUTION (yellow)
 * - < 30: SKIP (red)
 *
 * @param score - The overall score of the idea (0-100)
 * @returns Verdict object with text and color
 */
export const getVerdict = (score: number): Verdict => {
  if (score >= 75) return { text: "STRONG BUILD", color: "#00FF88" };
  if (score >= 50) return { text: "EXPLORING", color: "#00D4FF" };
  if (score >= 30) return { text: "CAUTION", color: "#FFB800" };
  return { text: "SKIP", color: "#FF4757" };
};

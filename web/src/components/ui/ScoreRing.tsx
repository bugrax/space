"use client";

import React from "react";
import styles from "../../app/page.module.css";

/**
 * Props for the ScoreRing component
 */
export interface ScoreRingProps {
  /** The score to display (0-100) */
  score: number;
  /** The size of the ring in pixels (default: 60) */
  size?: number;
}

/**
 * ScoreRing - A circular SVG progress indicator that visualizes a score
 *
 * Displays a score from 0-100 as a circular progress ring with color-coded
 * visual feedback. The ring color changes based on score thresholds:
 * - >= 75: Green (#00FF88) - Strong/Excellent
 * - >= 50: Blue (#00D4FF) - Good/Exploring
 * - >= 30: Yellow (#FFB800) - Caution/Warning
 * - < 30: Red (#FF4757) - Poor/Skip
 *
 * @param props - Component props
 * @returns A circular progress ring with centered score value
 *
 * @example
 * ```tsx
 * <ScoreRing score={85} size={60} />
 * <ScoreRing score={42} /> // Uses default size of 60
 * ```
 */
export const ScoreRing: React.FC<ScoreRingProps> = ({ score, size = 60 }) => {
  const radius = (size - 8) / 2;
  const circumference = 2 * Math.PI * radius;
  const progress = (score / 100) * circumference;
  const color =
    score >= 75
      ? "#00FF88"
      : score >= 50
      ? "#00D4FF"
      : score >= 30
      ? "#FFB800"
      : "#FF4757";

  return (
    <div
      className={styles.scoreRingContainer}
      style={{ width: size, height: size }}
    >
      <svg width={size} height={size}>
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="rgba(255,255,255,0.1)"
          strokeWidth="4"
        />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke={color}
          strokeWidth="4"
          strokeDasharray={circumference}
          strokeDashoffset={circumference - progress}
          strokeLinecap="round"
          transform={`rotate(-90 ${size / 2} ${size / 2})`}
          style={{ filter: `drop-shadow(0 0 6px ${color})` }}
        />
      </svg>
      <span className={styles.scoreValue} style={{ color }}>
        {score}
      </span>
    </div>
  );
};

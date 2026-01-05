"use client";

import React from "react";
import { LucideIcon } from "lucide-react";
import styles from "../../app/page.module.css";

/**
 * Props for the StatCard component
 */
export interface StatCardProps {
  /** The label/title for the stat */
  label: string;
  /** The main value to display */
  value: string;
  /** Change indicator or secondary text */
  change: string;
  /** Lucide icon component to display */
  icon: LucideIcon;
  /** Color theme for the card (hex color) */
  color: string;
}

/**
 * StatCard - A metric display card with an icon, value, and change indicator
 *
 * Displays a key metric or statistic with an icon, main value, and a change
 * indicator. The card includes visual effects like a colored icon background
 * and a subtle glow effect. Used to show dashboard KPIs and statistics.
 *
 * @param props - Component props
 * @returns A styled card displaying a statistic with icon and metadata
 *
 * @example
 * ```tsx
 * <StatCard
 *   label="Ideas Found"
 *   value="42"
 *   change="5 with MRR"
 *   icon={Sparkles}
 *   color="#00FF88"
 * />
 * ```
 */
export const StatCard: React.FC<StatCardProps> = ({
  label,
  value,
  change,
  icon: Icon,
  color,
}) => (
  <div className={styles.statCard}>
    <div
      className={styles.statIcon}
      style={{ background: `${color}15`, color }}
    >
      <Icon size={20} />
    </div>
    <div className={styles.statContent}>
      <span className={styles.statLabel}>{label}</span>
      <span className={styles.statValue}>{value}</span>
      <span className={styles.statChange} style={{ color }}>
        {change}
      </span>
    </div>
    <div className={styles.statGlow} style={{ background: color }} />
  </div>
);

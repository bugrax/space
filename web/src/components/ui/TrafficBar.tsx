"use client";

import React from "react";
import { TrafficData } from "@/types/dashboard";
import styles from "../../app/page.module.css";

/**
 * Props for the TrafficBar component
 */
export interface TrafficBarProps {
  /** Traffic source distribution data, or null if unavailable */
  traffic: TrafficData | null;
}

/**
 * TrafficBar - A horizontal bar visualization showing traffic source distribution
 *
 * Displays traffic distribution across four sources as a segmented horizontal bar:
 * - Organic: Search engine traffic
 * - Paid: Paid advertising traffic
 * - Social: Social media traffic
 * - Direct: Direct traffic
 *
 * Each segment is color-coded and sized proportionally to its percentage.
 * Displays "N/A" when traffic data is unavailable.
 *
 * @param props - Component props
 * @returns A horizontal bar with color-coded traffic segments
 *
 * @example
 * ```tsx
 * <TrafficBar traffic={{ organic: 40, paid: 30, social: 20, direct: 10 }} />
 * <TrafficBar traffic={null} /> // Shows "N/A"
 * ```
 */
export const TrafficBar: React.FC<TrafficBarProps> = ({ traffic }) => {
  if (!traffic) {
    return (
      <div className={styles.trafficBar}>
        <div className={styles.trafficNA}>N/A</div>
      </div>
    );
  }
  return (
    <div className={styles.trafficBar}>
      <div
        className={`${styles.trafficSegment} ${styles.organic}`}
        style={{ width: `${traffic.organic}%` }}
        title={`Organic: ${traffic.organic}%`}
      />
      <div
        className={`${styles.trafficSegment} ${styles.paid}`}
        style={{ width: `${traffic.paid}%` }}
        title={`Paid: ${traffic.paid}%`}
      />
      <div
        className={`${styles.trafficSegment} ${styles.social}`}
        style={{ width: `${traffic.social}%` }}
        title={`Social: ${traffic.social}%`}
      />
      <div
        className={`${styles.trafficSegment} ${styles.direct}`}
        style={{ width: `${traffic.direct}%` }}
        title={`Direct: ${traffic.direct}%`}
      />
    </div>
  );
};

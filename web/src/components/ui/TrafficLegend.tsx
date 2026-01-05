"use client";

import React from "react";
import styles from "../../app/page.module.css";

/**
 * TrafficLegend - A legend component showing traffic source color coding
 *
 * Displays a horizontal legend with color-coded indicators for the four traffic sources:
 * - Organic: Search engine traffic
 * - Paid: Paid advertising traffic
 * - Social: Social media traffic
 * - Direct: Direct traffic
 *
 * This component has no props and renders a static legend that corresponds
 * to the TrafficBar component's color scheme.
 *
 * @returns A horizontal legend with four color-coded traffic type indicators
 *
 * @example
 * ```tsx
 * <TrafficLegend />
 * ```
 */
export const TrafficLegend: React.FC = () => (
  <div className={styles.trafficLegend}>
    <div className={styles.legendItem}>
      <span className={`${styles.legendDot} ${styles.organic}`} />
      <span>Organic</span>
    </div>
    <div className={styles.legendItem}>
      <span className={`${styles.legendDot} ${styles.paid}`} />
      <span>Paid</span>
    </div>
    <div className={styles.legendItem}>
      <span className={`${styles.legendDot} ${styles.social}`} />
      <span>Social</span>
    </div>
    <div className={styles.legendItem}>
      <span className={`${styles.legendDot} ${styles.direct}`} />
      <span>Direct</span>
    </div>
  </div>
);

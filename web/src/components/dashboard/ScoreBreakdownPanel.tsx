"use client";

import React from "react";
import { ScoreRing } from "@/components/ui";
import { Idea } from "@/types/dashboard";
import { getVerdict } from "@/lib/utils";
import styles from "../../app/page.module.css";

/**
 * Props for the ScoreBreakdownPanel component
 */
export interface ScoreBreakdownPanelProps {
  /** The idea to display the score breakdown for, or null to hide the panel */
  idea: Idea | null;
}

/**
 * ScoreBreakdownPanel - Sidebar panel showing detailed score breakdown
 *
 * Displays a comprehensive breakdown of an idea's score including individual
 * components (traction, growth, traffic quality, simplicity), overall verdict,
 * replicability notes, and engagement statistics.
 *
 * The panel shows:
 * - Product name header
 * - Score breakdown bars for each component with color-coded visualization
 * - Total score ring with verdict
 * - Replicability assessment (if available)
 * - Social engagement metrics (likes, retweets, replies)
 *
 * @param props - Component props
 * @returns A sidebar panel with detailed score information, or null if no idea is selected
 *
 * @example
 * ```tsx
 * <ScoreBreakdownPanel idea={selectedIdea} />
 * <ScoreBreakdownPanel idea={null} /> // Panel hidden
 * ```
 */
export const ScoreBreakdownPanel: React.FC<ScoreBreakdownPanelProps> = ({
  idea,
}) => {
  if (!idea) return null;

  const totalScore =
    typeof idea.score === "object"
      ? idea.score_breakdown?.traction +
        idea.score_breakdown?.growth +
        idea.score_breakdown?.traffic +
        idea.score_breakdown?.simplicity
      : idea.score;
  const verdict = getVerdict(totalScore);

  const breakdownItems = [
    {
      label: "Traction",
      score: idea.score_breakdown?.traction || 0,
      max: 30,
      color: "#00FF88",
    },
    {
      label: "Growth Signal",
      score: idea.score_breakdown?.growth || 0,
      max: 25,
      color: "#00D4FF",
    },
    {
      label: "Traffic Quality",
      score: idea.score_breakdown?.traffic || 0,
      max: 25,
      color: "#B76EFF",
    },
    {
      label: "Simplicity",
      score: idea.score_breakdown?.simplicity || 0,
      max: 20,
      color: "#FFB800",
    },
  ];

  return (
    <div className={styles.scoreBreakdownPanel}>
      <div className={styles.panelHeader}>
        <h3>Score Breakdown</h3>
        <span className={styles.panelSubtitle}>{idea.product_name}</span>
      </div>
      <div className={styles.breakdownItems}>
        {breakdownItems.map((item, i) => (
          <div key={i} className={styles.breakdownItem}>
            <div className={styles.breakdownHeader}>
              <span className={styles.breakdownLabel}>{item.label}</span>
              <span
                className={styles.breakdownScore}
                style={{ color: item.color }}
              >
                {item.score}/{item.max}
              </span>
            </div>
            <div className={styles.breakdownBarBg}>
              <div
                className={styles.breakdownBarFill}
                style={{
                  width: `${(item.score / item.max) * 100}%`,
                  background: item.color,
                  boxShadow: `0 0 10px ${item.color}50`,
                }}
              />
            </div>
          </div>
        ))}
      </div>

      <div className={styles.totalScoreDisplay}>
        <ScoreRing score={totalScore} size={100} />
        <div className={styles.verdictDisplay} style={{ color: verdict.color }}>
          {verdict.text}
        </div>
      </div>

      {idea.replicability_note && (
        <div className={styles.replicabilityNote}>
          <span className={styles.replicabilityLabel}>
            Replicability: {idea.replicability}
          </span>
          <p>{idea.replicability_note}</p>
        </div>
      )}

      {idea.engagement && (
        <div className={styles.engagementStats}>
          <div className={styles.engagementItem}>
            <span>❤️</span> {idea.engagement.likes}
          </div>
          <div className={styles.engagementItem}>
            <span>🔄</span> {idea.engagement.retweets}
          </div>
          <div className={styles.engagementItem}>
            <span>💬</span> {idea.engagement.replies}
          </div>
        </div>
      )}
    </div>
  );
};

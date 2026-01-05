"use client";

import React from "react";
import { Globe, Twitter, ExternalLink, Star } from "lucide-react";
import { ScoreRing, TrafficBar } from "@/components/ui";
import { Idea } from "@/types/dashboard";
import { getVerdict } from "@/lib/utils";
import styles from "../../app/page.module.css";

/**
 * Props for the IdeaRow component
 */
export interface IdeaRowProps {
  /** The idea data to display */
  idea: Idea;
  /** Whether this row is currently selected */
  isSelected: boolean;
  /** Callback when the row is selected */
  onSelect: (id: number) => void;
  /** Callback when the favorite button is clicked */
  onFavorite: (id: number) => void;
}

/**
 * IdeaRow - Table row component displaying a SaaS idea with actions
 *
 * Renders a single row in the ideas table with all relevant information about
 * a SaaS idea including name, category, MRR, score, verdict, traffic sources,
 * author, and action buttons. Supports selection and favoriting.
 *
 * The row displays:
 * - Product name and URL with icon
 * - Category badge
 * - Monthly Recurring Revenue (MRR)
 * - Score ring visualization
 * - Verdict badge (color-coded recommendation)
 * - Traffic source distribution bar
 * - Author information with Twitter icon
 * - Date found
 * - Action buttons (external link, tweet link, favorite)
 *
 * @param props - Component props
 * @returns A table row element with idea data and interactive elements
 *
 * @example
 * ```tsx
 * <IdeaRow
 *   idea={ideaData}
 *   isSelected={selectedId === ideaData.id}
 *   onSelect={(id) => setSelectedId(id)}
 *   onFavorite={handleFavorite}
 * />
 * ```
 */
export const IdeaRow: React.FC<IdeaRowProps> = ({
  idea,
  isSelected,
  onSelect,
  onFavorite,
}) => {
  const totalScore =
    typeof idea.score === "object"
      ? idea.score_breakdown?.traction +
        idea.score_breakdown?.growth +
        idea.score_breakdown?.traffic +
        idea.score_breakdown?.simplicity
      : idea.score;
  const verdict = getVerdict(totalScore);
  // tweet_url is the actual Twitter link, found_in_tweet is the tweet text
  const tweetUrl = idea.tweet_url || "";

  return (
    <tr
      className={`${styles.ideaRow} ${isSelected ? styles.selected : ""}`}
      onClick={() => onSelect(idea.id)}
    >
      <td>
        <div className={styles.ideaNameCell}>
          <div className={styles.ideaFavicon}>
            <Globe size={16} />
          </div>
          <div className={styles.ideaNameInfo}>
            <span className={styles.ideaName}>
              {idea.product_name || "Unknown"}
            </span>
            <span className={styles.ideaUrl}>
              {idea.product_domain || idea.product_url || "N/A"}
            </span>
          </div>
        </div>
      </td>
      <td>
        <span className={styles.categoryBadge}>{idea.category || "Other"}</span>
      </td>
      <td>
        <div className={styles.mrrCell}>
          <span className={styles.mrrValue}>
            {idea.reported_mrr
              ? `$${idea.reported_mrr.toLocaleString()}`
              : "N/A"}
          </span>
        </div>
      </td>
      <td>
        <ScoreRing score={totalScore} size={44} />
      </td>
      <td>
        <span
          className={styles.verdictBadge}
          style={{
            background: `${verdict.color}15`,
            color: verdict.color,
            boxShadow: `0 0 20px ${verdict.color}20`,
          }}
        >
          {verdict.text}
        </span>
      </td>
      <td>
        <TrafficBar traffic={idea.traffic_source} />
      </td>
      <td>
        <div className={styles.authorCell}>
          <Twitter size={14} className={styles.authorIcon} />
          <span>{idea.author}</span>
        </div>
      </td>
      <td>
        <span className={styles.timeAgo}>
          {new Date(idea.date_found).toLocaleDateString()}
        </span>
      </td>
      <td>
        <div className={styles.rowActions}>
          {idea.product_url && (
            <a
              href={idea.product_url}
              target="_blank"
              rel="noopener noreferrer"
              className={styles.actionBtn}
              title="Open URL"
              onClick={(e) => e.stopPropagation()}
            >
              <ExternalLink size={16} />
            </a>
          )}
          {tweetUrl && (
            <a
              href={tweetUrl}
              target="_blank"
              rel="noopener noreferrer"
              className={styles.actionBtn}
              title="View Tweet"
              onClick={(e) => e.stopPropagation()}
            >
              <Twitter size={16} />
            </a>
          )}
          <button
            className={`${styles.actionBtn} ${
              idea.is_favorited ? styles.starred : styles.star
            }`}
            title="Add to Watchlist"
            onClick={(e) => {
              e.stopPropagation();
              onFavorite(idea.id);
            }}
          >
            <Star size={16} fill={idea.is_favorited ? "#FFB800" : "none"} />
          </button>
        </div>
      </td>
    </tr>
  );
};

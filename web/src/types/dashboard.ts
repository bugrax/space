/**
 * Represents traffic source distribution data for a product
 */
export interface TrafficData {
  /** Percentage of organic search traffic (0-100) */
  organic: number;
  /** Percentage of paid advertising traffic (0-100) */
  paid: number;
  /** Percentage of social media traffic (0-100) */
  social: number;
  /** Percentage of direct traffic (0-100) */
  direct: number;
}

/**
 * Breakdown of individual score components for an idea
 */
export interface ScoreBreakdown {
  /** Traction score (0-30) - measures product market validation */
  traction: number;
  /** Growth signal score (0-25) - measures momentum and growth indicators */
  growth: number;
  /** Traffic quality score (0-25) - measures traffic sources and sustainability */
  traffic: number;
  /** Simplicity score (0-20) - measures implementation complexity */
  simplicity: number;
}

/**
 * Social media engagement metrics for a tweet
 */
export interface Engagement {
  /** Number of likes on the tweet */
  likes: number;
  /** Number of retweets */
  retweets: number;
  /** Number of replies */
  replies: number;
  /** Engagement rate as a formatted string (e.g., "2.5%") */
  rate: string;
}

/**
 * Represents a SaaS idea discovered from Twitter
 */
export interface Idea {
  /** Unique identifier for the idea */
  id: number;
  /** Name of the product */
  product_name: string;
  /** Product website URL */
  product_url: string | null;
  /** Domain extracted from product URL */
  product_domain: string | null;
  /** Original tweet text where the product was mentioned */
  found_in_tweet?: string;
  /** Direct link to the source tweet */
  tweet_url?: string;
  /** Twitter username of the person who tweeted */
  author: string;
  /** Number of followers the author has */
  author_followers: number;
  /** Reported monthly recurring revenue in USD */
  reported_mrr: number | null;
  /** Overall score (can be a number or ScoreBreakdown object) */
  score: number | ScoreBreakdown;
  /** Letter grade based on score (A, B, C, etc.) */
  grade: string;
  /** Detailed breakdown of the score components */
  score_breakdown: ScoreBreakdown;
  /** Social engagement metrics for the source tweet */
  engagement: Engagement;
  /** Traffic source distribution data */
  traffic_source: TrafficData | null;
  /** Whether the idea has a screenshot available */
  has_screenshot: boolean;
  /** How easily the idea can be replicated (Low, Medium, High) */
  replicability: string;
  /** Additional notes about replicability */
  replicability_note: string | null;
  /** Product category (e.g., "SaaS", "Tool", "Service") */
  category: string | null;
  /** Implementation complexity level */
  complexity: string;
  /** Date when the idea was discovered and saved */
  date_found: string;
  /** Date when the original tweet was posted */
  tweet_date: string;
  /** Whether the user has favorited this idea */
  is_favorited?: boolean;
}

/**
 * Dashboard statistics and aggregated metrics
 */
export interface Stats {
  /** Total number of ideas in the database */
  total_ideas: number;
  /** Number of ideas with reported MRR data */
  with_mrr: number;
  /** Number of ideas with score >= 70 */
  high_score_ideas: number;
  /** Number of ideas marked as favorites */
  favorites: number;
  /** Average MRR across all ideas with MRR data */
  average_mrr: number;
  /** Average score across all ideas */
  average_score: number;
}

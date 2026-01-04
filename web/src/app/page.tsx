"use client";

import React, { useState, useEffect } from "react";
import useSWR from "swr";
import {
  Search,
  Filter,
  TrendingUp,
  DollarSign,
  Eye,
  Target,
  Bell,
  Settings,
  ChevronDown,
  ExternalLink,
  Star,
  Clock,
  Zap,
  BarChart3,
  PieChart,
  ArrowUpRight,
  ArrowDownRight,
  Sparkles,
  Radar,
  Globe,
  Twitter,
  RefreshCw,
  Loader2,
  AlertCircle,
  Check,
} from "lucide-react";
import styles from "./page.module.css";

// Types
interface TrafficData {
  organic: number;
  paid: number;
  social: number;
  direct: number;
}

interface ScoreBreakdown {
  traction: number;
  growth: number;
  traffic: number;
  simplicity: number;
}

interface Engagement {
  likes: number;
  retweets: number;
  replies: number;
  rate: string;
}

interface Idea {
  id: number;
  product_name: string;
  product_url: string | null;
  product_domain: string | null;
  found_in_tweet?: string;
  tweet_url?: string;
  author: string;
  author_followers: number;
  reported_mrr: number | null;
  score: number | ScoreBreakdown;
  grade: string;
  score_breakdown: ScoreBreakdown;
  engagement: Engagement;
  traffic_source: TrafficData | null;
  has_screenshot: boolean;
  replicability: string;
  replicability_note: string | null;
  category: string | null;
  complexity: string;
  date_found: string;
  tweet_date: string;
  is_favorited?: boolean;
}

interface Stats {
  total_ideas: number;
  with_mrr: number;
  high_score_ideas: number;
  favorites: number;
  average_mrr: number;
  average_score: number;
}

// API Base URL - use environment variable or default to localhost
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// API fetcher with base URL
const fetcher = (url: string) => {
  const fullUrl = url.startsWith("/api") ? `${API_BASE_URL}${url}` : url;
  return fetch(fullUrl).then((res) => res.json());
};

// Stat Card Component
const StatCard = ({
  label,
  value,
  change,
  icon: Icon,
  color,
}: {
  label: string;
  value: string;
  change: string;
  icon: any;
  color: string;
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

// Score Ring Component
const ScoreRing = ({ score, size = 60 }: { score: number; size?: number }) => {
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

// Traffic Bar Component
const TrafficBar = ({ traffic }: { traffic: TrafficData | null }) => {
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

// Verdict helpers
const getVerdict = (score: number) => {
  if (score >= 75) return { text: "STRONG BUILD", color: "#00FF88" };
  if (score >= 50) return { text: "EXPLORING", color: "#00D4FF" };
  if (score >= 30) return { text: "CAUTION", color: "#FFB800" };
  return { text: "SKIP", color: "#FF4757" };
};

// Idea Row Component
const IdeaRow = ({
  idea,
  isSelected,
  onSelect,
  onFavorite,
}: {
  idea: Idea;
  isSelected: boolean;
  onSelect: (id: number) => void;
  onFavorite: (id: number) => void;
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

// Score Breakdown Panel
const ScoreBreakdownPanel = ({ idea }: { idea: Idea | null }) => {
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

// Traffic Legend Component
const TrafficLegend = () => (
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

// Main Dashboard Component
export default function Dashboard() {
  const [selectedIdea, setSelectedIdea] = useState<Idea | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [activeFilter, setActiveFilter] = useState("all");
  const [isScanning, setIsScanning] = useState(false);
  const [scanStatus, setScanStatus] = useState<string | null>(null);

  // Fetch ideas
  const {
    data: ideasData,
    error: ideasError,
    mutate: mutateIdeas,
  } = useSWR<Idea[]>(
    `/api/ideas?min_score=${activeFilter === "strong" ? 70 : 0}${
      activeFilter === "favorites" ? "&favorites=true" : ""
    }`,
    fetcher,
    { refreshInterval: 30000 }
  );

  // Fetch stats
  const { data: statsData } = useSWR<Stats>("/api/stats", fetcher, {
    refreshInterval: 60000,
  });

  const ideas = ideasData || [];
  const stats = statsData || {
    total_ideas: 0,
    with_mrr: 0,
    high_score_ideas: 0,
    favorites: 0,
    average_mrr: 0,
    average_score: 0,
  };

  // Set first idea as selected when ideas load
  useEffect(() => {
    if (ideas.length > 0 && !selectedIdea) {
      setSelectedIdea(ideas[0]);
    }
  }, [ideas, selectedIdea]);

  const filters = [
    { key: "all", label: "All Ideas", count: stats.total_ideas },
    { key: "strong", label: "Strong Build", count: stats.high_score_ideas },
    { key: "favorites", label: "Favorites", count: stats.favorites },
  ];

  // Handle scan
  const handleScan = async () => {
    setIsScanning(true);
    setScanStatus("Scanning Twitter...");

    try {
      const response = await fetch(`${API_BASE_URL}/api/scan`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          hashtags: ["buildinpublic", "indiehackers", "saas"],
          days: 7,
        }),
      });

      const result = await response.json();
      setScanStatus(
        `Found ${result.total_found} ideas, ${result.new_saved} new!`
      );
      mutateIdeas();

      setTimeout(() => setScanStatus(null), 3000);
    } catch (error) {
      setScanStatus("Scan failed");
      setTimeout(() => setScanStatus(null), 3000);
    } finally {
      setIsScanning(false);
    }
  };

  // Handle favorite
  const handleFavorite = async (id: number) => {
    try {
      await fetch(`${API_BASE_URL}/api/ideas/${id}/favorite`, {
        method: "POST",
      });
      mutateIdeas();
    } catch (error) {
      console.error("Failed to toggle favorite");
    }
  };

  // Filter ideas by search
  const filteredIdeas = ideas.filter((idea) => {
    if (!searchQuery) return true;
    const q = searchQuery.toLowerCase();
    return (
      idea.product_name?.toLowerCase().includes(q) ||
      idea.author?.toLowerCase().includes(q) ||
      idea.category?.toLowerCase().includes(q)
    );
  });

  const statCards = [
    {
      label: "Ideas Found",
      value: stats.total_ideas.toString(),
      change: `${stats.with_mrr} with MRR`,
      icon: Sparkles,
      color: "#00FF88",
    },
    {
      label: "High Score (70+)",
      value: stats.high_score_ideas.toString(),
      change: "Strong builds",
      icon: Target,
      color: "#00D4FF",
    },
    {
      label: "Total MRR Tracked",
      value: `$${Math.round((stats.average_mrr * stats.with_mrr) / 1000)}K`,
      change: `Avg $${Math.round(stats.average_mrr)}`,
      icon: DollarSign,
      color: "#FF6B00",
    },
    {
      label: "Avg Score",
      value: stats.average_score.toFixed(0),
      change: "out of 100",
      icon: BarChart3,
      color: "#B76EFF",
    },
  ];

  return (
    <div className={styles.dashboard}>
      {/* Ambient Background Effects */}
      <div className={styles.ambientBg}>
        <div className={`${styles.glowOrb} ${styles.orb1}`} />
        <div className={`${styles.glowOrb} ${styles.orb2}`} />
        <div className={`${styles.glowOrb} ${styles.orb3}`} />
        <div className={styles.gridOverlay} />
      </div>

      {/* Sidebar */}
      <aside className={styles.sidebar}>
        <div className={styles.logo}>
          <Radar className={styles.logoIcon} />
          <span className={styles.logoText}>IdeaRadar</span>
        </div>

        <nav className={styles.navMenu}>
          <a href="#" className={`${styles.navItem} ${styles.active}`}>
            <Sparkles size={18} />
            <span>Discover</span>
          </a>
          <a
            href="#"
            className={styles.navItem}
            onClick={() => setActiveFilter("favorites")}
          >
            <Star size={18} />
            <span>Watchlist</span>
            {stats.favorites > 0 && (
              <span className={styles.navBadge}>{stats.favorites}</span>
            )}
          </a>
          <a href="#" className={styles.navItem}>
            <TrendingUp size={18} />
            <span>Trending</span>
          </a>
          <a href="#" className={styles.navItem}>
            <BarChart3 size={18} />
            <span>Analytics</span>
          </a>
        </nav>

        <div className={styles.sidebarFooter}>
          <a href="#" className={styles.navItem}>
            <Settings size={18} />
            <span>Settings</span>
          </a>
        </div>
      </aside>

      {/* Main Content */}
      <main className={styles.mainContent}>
        {/* Header */}
        <header className={styles.header}>
          <div className={styles.headerLeft}>
            <h1>Discover Ideas</h1>
            <p className={styles.headerSubtitle}>
              Find validated SaaS opportunities from Twitter
            </p>
          </div>
          <div className={styles.headerRight}>
            <div className={styles.searchBox}>
              <Search size={18} className={styles.searchIcon} />
              <input
                type="text"
                placeholder="Search ideas, authors, categories..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
              />
            </div>
            <button
              className={styles.scanBtn}
              onClick={handleScan}
              disabled={isScanning}
            >
              {isScanning ? (
                <Loader2 size={16} className={styles.spinning} />
              ) : (
                <RefreshCw size={16} />
              )}
              <span>{scanStatus || "Scan Now"}</span>
            </button>
          </div>
        </header>

        {/* Stats Row */}
        <section className={styles.statsRow}>
          {statCards.map((stat, i) => (
            <StatCard key={i} {...stat} />
          ))}
        </section>

        {/* Content Grid */}
        <div className={styles.contentGrid}>
          {/* Ideas Table Section */}
          <section className={styles.ideasSection}>
            {/* Filter Tabs */}
            <div className={styles.filterTabs}>
              {filters.map((filter) => (
                <button
                  key={filter.key}
                  className={`${styles.filterTab} ${
                    activeFilter === filter.key ? styles.active : ""
                  }`}
                  onClick={() => setActiveFilter(filter.key)}
                >
                  {filter.label}
                  <span className={styles.filterCount}>{filter.count}</span>
                </button>
              ))}

              <div className={styles.filterActions}>
                <TrafficLegend />
              </div>
            </div>

            {/* Ideas Table */}
            <div className={styles.tableContainer}>
              {ideasError ? (
                <div className={styles.errorState}>
                  <AlertCircle size={48} />
                  <p>
                    Failed to load ideas. Make sure the API server is running.
                  </p>
                </div>
              ) : ideas.length === 0 ? (
                <div className={styles.emptyState}>
                  <Sparkles size={48} />
                  <p>
                    No ideas found yet. Click "Scan Now" to discover SaaS ideas!
                  </p>
                </div>
              ) : (
                <table className={styles.ideasTable}>
                  <thead>
                    <tr>
                      <th>Product</th>
                      <th>Category</th>
                      <th>MRR</th>
                      <th>Score</th>
                      <th>Verdict</th>
                      <th>Traffic</th>
                      <th>Source</th>
                      <th>Found</th>
                      <th>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredIdeas.map((idea) => (
                      <IdeaRow
                        key={idea.id}
                        idea={idea}
                        isSelected={selectedIdea?.id === idea.id}
                        onSelect={(id) =>
                          setSelectedIdea(
                            filteredIdeas.find((i) => i.id === id) || null
                          )
                        }
                        onFavorite={handleFavorite}
                      />
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          </section>

          {/* Score Breakdown Sidebar */}
          <ScoreBreakdownPanel idea={selectedIdea} />
        </div>
      </main>
    </div>
  );
}

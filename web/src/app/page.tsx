"use client";

import React, { useState, useEffect } from "react";
import useSWR from "swr";
import {
  Search,
  TrendingUp,
  DollarSign,
  Target,
  Settings,
  Star,
  BarChart3,
  Sparkles,
  Radar,
  RefreshCw,
  Loader2,
  AlertCircle,
} from "lucide-react";
import styles from "./page.module.css";

// Type imports
import type { Idea, Stats } from "@/types";

// API utilities
import { API_BASE_URL, fetcher } from "@/lib/api";

// UI components
import { StatCard, TrafficLegend } from "@/components/ui";

// Dashboard components
import { IdeaRow, ScoreBreakdownPanel } from "@/components/dashboard";

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
      // Silently handle favorite toggle errors
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

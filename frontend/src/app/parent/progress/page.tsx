"use client";

import { useEffect, useState } from "react";

import { AppShell } from "@/components/app-shell";
import { Card } from "@/components/card";
import { Split, StatGrid } from "@/components/layout";
import { ApiError, getParentProgress, type ParentProgressResponse } from "@/lib/api";
import { parentProgressHighlights, recentSessions } from "@/lib/mock-data";

import styles from "../../screens.module.css";

export default function ParentProgressPage() {
  const [progress, setProgress] = useState<ParentProgressResponse | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    const run = async () => {
      try {
        const payload = await getParentProgress();
        setProgress(payload);
      } catch (err) {
        if (err instanceof ApiError && err.status === 401) {
          window.location.href = "/login";
          return;
        }
        setError("Could not load live parent progress. Showing local preview.");
      }
    };
    void run();
  }, []);

  const totalActivities = progress?.summary.session_count ?? parentProgressHighlights.totalActivities;
  const strongest = progress?.summary.skill_summary?.strength ?? parentProgressHighlights.strongestSkill;
  const growth = progress?.summary.skill_summary?.struggle ?? parentProgressHighlights.growthArea;
  const trend = progress?.summary.trend ?? "starting";
  const recent = progress
    ? progress.recent_sessions.map((session) => ({
        id: session.session_id,
        activityTitle: session.activity_title,
        scoreLabel: `${Math.round(session.score_percent)}%`,
        skill: progress.summary.strengths?.[0] ?? "reading-comprehension",
      }))
    : recentSessions;
  const writingFeedback = progress?.writing_feedback_summaries ?? [];

  return (
    <AppShell
      title="Parent progress snapshot"
      subtitle="Simple, practical trend view for recent reading and writing sessions."
    >
      {error ? (
        <p role="alert" className={styles.error}>
          {error}
        </p>
      ) : null}
      <Split>
        <Card as="article">
          <h2>Overview</h2>
          <StatGrid>
            <div className={styles.stat}>
              <span className={styles.statLabel}>Completed activities</span>
              <p className={styles.statValue}>{totalActivities}</p>
            </div>
            <div className={styles.stat}>
              <span className={styles.statLabel}>Strongest area</span>
              <p className={styles.statValue}>{strongest}</p>
            </div>
            <div className={styles.stat}>
              <span className={styles.statLabel}>Trend</span>
              <p className={styles.statValue}>{trend}</p>
            </div>
          </StatGrid>
          <p className={styles.muted}>Growth area: {growth}</p>
        </Card>

        <Card as="article">
          <h2>Recent sessions</h2>
          <ul className={styles.list}>
            {recent.length === 0 ? <li>No completed sessions yet.</li> : null}
            {recent.map((session) => (
              <li key={session.id}>
                {session.activityTitle} - {session.scoreLabel} ({session.skill})
              </li>
            ))}
          </ul>
        </Card>
        <Card as="article">
          <h2>Writing feedback highlights</h2>
          <ul className={styles.list}>
            {writingFeedback.length === 0 ? <li>No writing feedback yet.</li> : null}
            {writingFeedback.map((item, index) => (
              <li key={`${item.activity_title}-${index}`}>
                {item.activity_title}: {item.summary}
              </li>
            ))}
          </ul>
        </Card>
      </Split>
    </AppShell>
  );
}

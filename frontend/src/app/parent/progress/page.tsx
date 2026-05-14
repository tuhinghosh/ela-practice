"use client";

import { useEffect, useState } from "react";

import { AppShell } from "@/components/app-shell";
import { Card } from "@/components/card";
import { Icon } from "@/components/icon";
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
  const practiceNext = progress?.practice_next ?? [];
  const thirtyDay = progress?.skill_history?.["30_day"] ?? {};
  const thirtyDayEntries = Object.entries(thirtyDay)
    .map(([skill, stats]) => ({ skill, attempts: stats.attempts, avg: stats.avg_score }))
    .sort((a, b) => a.avg - b.avg);
  const recentQuestions = progress?.recent_questions ?? [];
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
      eyebrow="Parent view"
      heroIcon="trending-up"
    >
      {error ? (
        <p role="alert" className={styles.error}>
          <Icon name="message-circle" size={16} />
          {error}
        </p>
      ) : null}
      <Split>
        <Card as="article" className={styles.cardWithHeader}>
          <div className={styles.cardHeader}>
            <span className={styles.cardIcon} style={{ ["--icon-color" as string]: "var(--brand)" }}>
              <Icon name="trending-up" size={18} />
            </span>
            <h2>Overview</h2>
          </div>
          <StatGrid>
            <div className={styles.stat}>
              <span className={styles.statTopRow}>
                <Icon name="check-circle" size={14} />
                <span className={styles.statLabel}>Completed activities</span>
              </span>
              <p className={styles.statValue}>{totalActivities}</p>
            </div>
            <div className={styles.stat}>
              <span className={styles.statTopRow}>
                <Icon name="award" size={14} />
                <span className={styles.statLabel}>Strongest area</span>
              </span>
              <p className={styles.statValue}>{strongest}</p>
            </div>
            <div className={styles.stat}>
              <span className={styles.statTopRow}>
                <Icon name="trending-up" size={14} />
                <span className={styles.statLabel}>Trend</span>
              </span>
              <p className={styles.statValue}>
                <span className={styles.trendPill}>
                  <Icon name="trending-up" size={12} />
                  {trend}
                </span>
              </p>
            </div>
          </StatGrid>
          <p className={styles.muted}>
            Growth area: <strong>{growth}</strong>
          </p>
        </Card>

        <Card as="article" className={styles.cardWithHeader}>
          <div className={styles.cardHeader}>
            <span className={styles.cardIcon} style={{ ["--icon-color" as string]: "var(--success)" }}>
              <Icon name="clipboard-list" size={18} />
            </span>
            <h2>Recent sessions</h2>
          </div>
          <ul className={styles.sessionList}>
            {recent.length === 0 ? (
              <li className={styles.emptyHint}>No completed sessions yet.</li>
            ) : null}
            {recent.map((session) => (
              <li key={session.id} className={styles.sessionItem}>
                <span className={styles.sessionTitle}>
                  {session.activityTitle} ({session.skill})
                </span>
                <span className={styles.sessionScore}>{session.scoreLabel}</span>
              </li>
            ))}
          </ul>
        </Card>
        <Card as="article" className={styles.cardWithHeader} aria-label="Practice next">
          <div className={styles.cardHeader}>
            <span className={styles.cardIcon} style={{ ["--icon-color" as string]: "var(--brand)" }}>
              <Icon name="trending-up" size={18} />
            </span>
            <h2>Practice next</h2>
          </div>
          {practiceNext.length === 0 ? (
            <p className={styles.muted}>
              No targeted suggestions yet — once your child completes a few more activities
              we&apos;ll point to the skills with the most room to grow.
            </p>
          ) : (
            <ul className={styles.sessionList}>
              {practiceNext.map((item) => (
                <li key={item.skill} className={styles.sessionItem}>
                  <span className={styles.sessionTitle}>{item.skill}</span>
                  <span className={styles.sessionScore}>
                    {Math.round(item.avg_score)}% over {item.attempts} attempts
                  </span>
                </li>
              ))}
            </ul>
          )}
        </Card>

        <Card as="article" className={styles.cardWithHeader} aria-label="Last 30 days by skill">
          <div className={styles.cardHeader}>
            <span className={styles.cardIcon} style={{ ["--icon-color" as string]: "var(--accent)" }}>
              <Icon name="trending-up" size={18} />
            </span>
            <h2>Last 30 days by skill</h2>
          </div>
          {thirtyDayEntries.length === 0 ? (
            <p className={styles.muted}>No skill data in the last 30 days yet.</p>
          ) : (
            <ul className={styles.sessionList}>
              {thirtyDayEntries.map((entry) => (
                <li key={entry.skill} className={styles.sessionItem}>
                  <span className={styles.sessionTitle}>{entry.skill}</span>
                  <span className={styles.sessionScore}>
                    {Math.round(entry.avg)}% ({entry.attempts})
                  </span>
                </li>
              ))}
            </ul>
          )}
        </Card>

        <Card as="article" className={styles.cardWithHeader}>
          <div className={styles.cardHeader}>
            <span className={styles.cardIcon} style={{ ["--icon-color" as string]: "var(--success)" }}>
              <Icon name="clipboard-list" size={18} />
            </span>
            <h2>Recent questions</h2>
          </div>
          {recentQuestions.length === 0 ? (
            <p className={styles.muted}>No recent questions yet.</p>
          ) : (
            <ul className={styles.feedbackList}>
              {recentQuestions.slice(0, 6).map((question) => {
                const badge =
                  question.is_correct === true
                    ? "Correct"
                    : question.is_correct === false
                    ? "Needs review"
                    : "Written response";
                return (
                  <li
                    key={`${question.session_id}-${question.question_id}`}
                    className={styles.feedbackItem}
                  >
                    <p className={styles.feedbackTitle}>
                      <Icon name="book" size={14} />
                      {question.activity_title} · {badge}
                    </p>
                    <p className={styles.feedbackSummary}>{question.prompt}</p>
                    {question.skill_tags.length > 0 ? (
                      <p className={styles.muted}>Skills: {question.skill_tags.join(", ")}</p>
                    ) : null}
                  </li>
                );
              })}
            </ul>
          )}
        </Card>

        <Card as="article" className={styles.cardWithHeader}>
          <div className={styles.cardHeader}>
            <span className={styles.cardIcon} style={{ ["--icon-color" as string]: "var(--accent)" }}>
              <Icon name="pencil" size={18} />
            </span>
            <h2>Writing feedback highlights</h2>
          </div>
          <ul className={styles.feedbackList}>
            {writingFeedback.length === 0 ? (
              <li className={styles.emptyHint}>No writing feedback yet.</li>
            ) : null}
            {writingFeedback.map((item, index) => (
              <li key={`${item.activity_title}-${index}`} className={styles.feedbackItem}>
                <p className={styles.feedbackTitle}>
                  <Icon name="book" size={14} />
                  {item.activity_title}
                </p>
                <p className={styles.feedbackSummary}>{item.summary}</p>
              </li>
            ))}
          </ul>
        </Card>
      </Split>
    </AppShell>
  );
}

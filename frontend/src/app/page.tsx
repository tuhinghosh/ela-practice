"use client";

import { useEffect, useState } from "react";

import { AppShell } from "@/components/app-shell";
import { Button, ButtonLink } from "@/components/button";
import { Card } from "@/components/card";
import { Split, Stack, StatGrid } from "@/components/layout";
import { Tag } from "@/components/tag";
import { ApiError, type ActivitiesResponse, type DashboardResponse, getDashboard, listActivities } from "@/lib/api";
import { activities as fallbackActivities, recentSessions, rewardSnapshot } from "@/lib/mock-data";

import styles from "./screens.module.css";

export default function Home() {
  const [dashboard, setDashboard] = useState<DashboardResponse | null>(null);
  const [availableThemes, setAvailableThemes] = useState<string[]>([]);
  const [availableDifficulties, setAvailableDifficulties] = useState<Array<"easy" | "medium" | "difficult">>([]);
  const [activityList, setActivityList] = useState<ActivitiesResponse["activities"]>([]);
  const [selectedTheme, setSelectedTheme] = useState<string>("all");
  const [selectedDifficulty, setSelectedDifficulty] = useState<"all" | "easy" | "medium" | "difficult">("all");
  const [userSelectedActivityId, setUserSelectedActivityId] = useState<string | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    const run = async () => {
      try {
        const payload = await getDashboard();
        setDashboard(payload);
      } catch (err) {
        if (err instanceof ApiError && err.status === 401) {
          window.location.href = "/login";
          return;
        }
        setError("Could not load live dashboard data. Showing local preview data.");
      }
    };
    void run();
  }, []);

  useEffect(() => {
    const run = async () => {
      try {
        const payload = await listActivities({
          theme: selectedTheme === "all" ? undefined : selectedTheme,
          difficulty: selectedDifficulty === "all" ? undefined : selectedDifficulty,
        });
        setActivityList(payload.activities);
        setAvailableThemes(payload.themes);
        setAvailableDifficulties(payload.difficulties);
      } catch (err) {
        if (err instanceof ApiError && err.status === 401) {
          window.location.href = "/login";
          return;
        }
        setError("Could not load activity list. Showing local preview data.");
      }
    };
    void run();
  }, [selectedTheme, selectedDifficulty]);

  const availableActivities =
    activityList.length > 0
      ? activityList.map((activity) => ({
          id: activity.id,
          title: activity.title,
          theme: activity.theme,
          difficulty: activity.difficulty,
          missionLabel: activity.mission_label,
          skillTags: activity.skill_tags,
        }))
      : fallbackActivities.map((activity) => ({
          id: activity.id,
          title: activity.title,
          theme: activity.theme,
          difficulty: activity.difficulty,
          missionLabel: activity.missionLabel,
          skillTags: activity.skillTags,
        }));
  const difficultyOptions =
    availableDifficulties.length > 0 ? availableDifficulties : (["easy", "medium", "difficult"] as const);
  const fallbackThemes = Array.from(new Set(fallbackActivities.map((activity) => activity.theme)));
  const themeOptions = availableThemes.length > 0 ? availableThemes : fallbackThemes;
  const suggestedActivityId = typeof window !== "undefined" ? localStorage.getItem("ela:suggested-activity") : null;

  const attempted = new Set((dashboard?.recent_sessions ?? []).map((session) => session.activity_id));
  const suggested = availableActivities.find((activity) => activity.id === suggestedActivityId);
  const unattempted = availableActivities.find((activity) => !attempted.has(activity.id));
  const fromDashboard = availableActivities.find((activity) => activity.id === dashboard?.mission.activity_id);
  const autoSelectedActivityId = (suggested ?? unattempted ?? fromDashboard ?? availableActivities[0])?.id ?? null;
  const selectedActivityId =
    userSelectedActivityId && availableActivities.some((activity) => activity.id === userSelectedActivityId)
      ? userSelectedActivityId
      : autoSelectedActivityId;

  const selectedActivity =
    availableActivities.find((activity) => activity.id === selectedActivityId) ?? availableActivities[0] ?? null;

  const mission = selectedActivity
    ? {
        activityId: selectedActivity.id,
        difficulty: selectedActivity.difficulty,
        missionLabel:
          selectedActivity.id === suggestedActivityId
            ? `Coach quest unlocked: ${selectedActivity.title}`
            : selectedActivity.missionLabel,
        skillTags:
          selectedActivity.id === suggestedActivityId
            ? ["coach-suggested", ...(dashboard?.progress.growth_areas ?? []).slice(0, 2)]
            : selectedActivity.skillTags,
      }
    : {
        activityId: "nature-01",
        difficulty: "easy" as const,
        missionLabel: "Choose an activity to start your reading quest.",
        skillTags: [],
      };

  const rewards = dashboard
    ? {
        stars: dashboard.rewards.stars,
        streakDays: dashboard.rewards.streak_days,
        badges: dashboard.rewards.badges,
      }
    : rewardSnapshot;
  const points = rewards.stars * 10;

  const recent = dashboard
    ? dashboard.recent_sessions.map((session) => ({
        id: session.session_id,
        activityTitle: session.activity_title,
        scoreLabel: `${Math.round(session.score_percent)}%`,
      }))
    : recentSessions;

  return (
    <AppShell
      title="Welcome back, Reader!"
      subtitle="Your reading adventure is ready. Read closely, share your ideas, and collect stars."
    >
      <Stack>
        {error ? (
          <p role="alert" className={styles.error}>
            {error}
          </p>
        ) : null}
        <Card>
          <h2>Today&apos;s mission</h2>
          <p className={styles.difficultyLevel}>Difficulty level: {mission.difficulty.toUpperCase()}</p>
          <p className={styles.muted}>{mission.missionLabel}</p>
          <div>
            <label className={styles.label} htmlFor="theme-filter">
              Theme
            </label>
            <select
              id="theme-filter"
              className={styles.input}
              value={selectedTheme}
              onChange={(event) => {
                setSelectedTheme(event.target.value);
                setUserSelectedActivityId(null);
              }}
            >
              <option value="all">All themes</option>
              {themeOptions.map((theme) => (
                <option key={theme} value={theme}>
                  {theme}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className={styles.label} htmlFor="difficulty-filter">
              Difficulty
            </label>
            <select
              id="difficulty-filter"
              className={styles.input}
              value={selectedDifficulty}
              onChange={(event) => {
                setSelectedDifficulty(event.target.value as "all" | "easy" | "medium" | "difficult");
                setUserSelectedActivityId(null);
              }}
            >
              <option value="all">All levels</option>
              {difficultyOptions.map((difficulty) => (
                <option key={difficulty} value={difficulty}>
                  {difficulty}
                </option>
              ))}
            </select>
          </div>
          <div className={styles.chipRow}>
            {mission.skillTags.map((skill) => (
              <Tag key={skill}>{skill}</Tag>
            ))}
          </div>
          <ButtonLink href={`/activity/${mission.activityId}`}>
            Start mission
          </ButtonLink>
        </Card>

        <Split>
          <Card as="article">
            <h3>Reward tracker</h3>
            <StatGrid>
              <div className={styles.stat}>
                <span className={styles.statLabel}>Stars</span>
                <p className={styles.statValue}>{rewards.stars}</p>
              </div>
              <div className={styles.stat}>
                <span className={styles.statLabel}>Points</span>
                <p className={styles.statValue}>{points}</p>
              </div>
              <div className={styles.stat}>
                <span className={styles.statLabel}>Streak</span>
                <p className={styles.statValue}>{rewards.streakDays} days</p>
              </div>
            </StatGrid>
            <div className={styles.chipRow}>
              {rewards.badges.map((badge) => (
                <Tag key={badge}>{badge}</Tag>
              ))}
            </div>
          </Card>

          <Card as="article">
            <h3>Recent practice</h3>
            <ul className={styles.list}>
              {recent.length === 0 ? <li>No sessions yet. Start today&apos;s quest to begin your streak.</li> : null}
              {recent.map((session) => (
                <li key={session.id}>
                  {session.activityTitle} - {session.scoreLabel}
                </li>
              ))}
            </ul>
          </Card>

          <Card as="article">
            <h3>Available activities</h3>
            <ul className={styles.activityList}>
              {availableActivities.length === 0 ? <li>No activities available yet.</li> : null}
              {availableActivities.map((item) => (
                <li key={item.id} className={styles.activityItem}>
                  <div>
                    <strong>{item.title}</strong>
                    <div className={styles.muted}>Theme: {item.theme}</div>
                    <p className={styles.difficultyLevel}>Difficulty: {item.difficulty.toUpperCase()}</p>
                    {selectedActivityId === item.id ? <span className={styles.muted}> (Current mission)</span> : null}
                  </div>
                  <div className={styles.activityActions}>
                    <Button
                      type="button"
                      tone="ghost"
                      className={styles.inlineAction}
                      onClick={() => setUserSelectedActivityId(item.id)}
                    >
                      Set mission
                    </Button>
                    <ButtonLink href={`/activity/${item.id}`} tone="secondary" className={styles.inlineAction}>
                      Start now
                    </ButtonLink>
                  </div>
                </li>
              ))}
            </ul>
          </Card>
        </Split>
      </Stack>
    </AppShell>
  );
}

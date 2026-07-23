"use client";

import { useEffect, useState } from "react";

import { AppShell } from "@/components/app-shell";
import { Button, ButtonLink } from "@/components/button";
import { Card } from "@/components/card";
import { Icon } from "@/components/icon";
import { Split, Stack, StatGrid } from "@/components/layout";
import { Tag } from "@/components/tag";
import { ApiError, type ActivitiesResponse, type DashboardResponse, getDashboard, listActivities } from "@/lib/api";
import { activities as fallbackActivities, recentSessions, rewardSnapshot } from "@/lib/mock-data";

import styles from "./screens.module.css";

const DIFFICULTY_META: Record<"easy" | "medium" | "difficult", { label: string; color: string }> = {
  easy: { label: "Easy", color: "var(--success)" },
  medium: { label: "Medium", color: "var(--warning)" },
  difficult: { label: "Difficult", color: "var(--danger)" },
};

const REYANA_MISSION_IDS = [
  "pilot-mystery-cat-01",
  "pilot-space-mars-01",
  "pilot-world-japan-01",
] as const;

const REYANA_MISSION_META: Record<(typeof REYANA_MISSION_IDS)[number], { step: string; kicker: string }> = {
  "pilot-mystery-cat-01": { step: "Mission 1", kicker: "School mystery • Start here" },
  "pilot-space-mars-01": { step: "Mission 2", kicker: "Mars science • Next challenge" },
  "pilot-world-japan-01": { step: "Mission 3", kicker: "World geography • Final challenge" },
};

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
  const nextPilotId = REYANA_MISSION_IDS.find((id) => !attempted.has(id));
  const nextPilot = availableActivities.find((activity) => activity.id === nextPilotId);
  const unattempted = availableActivities.find((activity) => !attempted.has(activity.id));
  const fromDashboard = availableActivities.find((activity) => activity.id === dashboard?.mission.activity_id);
  const autoSelectedActivityId = (suggested ?? nextPilot ?? fromDashboard ?? unattempted ?? availableActivities[0])?.id ?? null;
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
        title: selectedActivity.title,
        theme: selectedActivity.theme,
        missionLabel:
          selectedActivity.id === suggestedActivityId
            ? `Coach quest unlocked: ${selectedActivity.title}`
            : selectedActivity.id === dashboard?.recommendation?.activity_id
              ? dashboard.recommendation.reason
            : selectedActivity.missionLabel,
        skillTags:
          selectedActivity.id === suggestedActivityId
            ? ["coach-suggested", ...(dashboard?.progress.growth_areas ?? []).slice(0, 2)]
            : selectedActivity.skillTags,
      }
    : {
        activityId: "nature-01",
        difficulty: "easy" as const,
        title: "Choose your adventure",
        theme: "nature",
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

  const missionDifficulty = DIFFICULTY_META[mission.difficulty] ?? DIFFICULTY_META.easy;

  return (
    <AppShell
      title="Welcome back, Reader!"
      subtitle="Your reading adventure is ready. Read closely, share your ideas, and collect stars."
      heroIcon="rocket"
    >
      <Stack>
        {error ? (
          <p role="alert" className={styles.error}>
            <Icon name="message-circle" size={16} />
            {error}
          </p>
        ) : null}

        <Card className={styles.pilotCard}>
          <div className={styles.pilotHeader}>
            <div>
              <span className={styles.cardEyebrow}>
                <Icon name="sparkles" size={12} />
                Three-part starter adventure
              </span>
              <h2 className={styles.missionTitle}>Reyana&apos;s Missions</h2>
              <p className={styles.muted}>Begin with the cat mystery, travel to Mars, then explore Japan.</p>
            </div>
            <span className={styles.pilotProgress}>
              {REYANA_MISSION_IDS.filter((id) => attempted.has(id)).length} of {REYANA_MISSION_IDS.length} complete
            </span>
          </div>
          <ol className={styles.pilotPath}>
            {REYANA_MISSION_IDS.map((id) => {
              const item = availableActivities.find((activity) => activity.id === id) ??
                fallbackActivities.find((activity) => activity.id === id);
              if (!item) return null;
              const complete = attempted.has(id);
              const isNext = id === nextPilotId;
              const meta = REYANA_MISSION_META[id];
              const difficulty = DIFFICULTY_META[item.difficulty];
              return (
                <li key={id} className={`${styles.pilotStep} ${isNext ? styles.pilotStepNext : ""}`}>
                  <span className={styles.pilotStepNumber} aria-hidden="true">
                    {complete ? <Icon name="check-circle" size={18} /> : meta.step.replace("Mission ", "")}
                  </span>
                  <div className={styles.pilotStepBody}>
                    <span className={styles.pilotKicker}>{meta.kicker}</span>
                    <strong>{item.title}</strong>
                    <span className={styles.activityMeta}>
                      <span
                        className={styles.metaPill}
                        style={{ ["--pill-color" as string]: difficulty.color }}
                      >
                        {difficulty.label}
                      </span>
                      {complete ? "Completed" : isNext ? "Up next" : "Ready when you are"}
                    </span>
                  </div>
                  <ButtonLink href={`/activity/${id}`} tone={isNext ? "primary" : "secondary"} className={styles.pilotAction}>
                    {complete ? "Practice again" : isNext ? "Start mission" : "Open"}
                    <Icon name="arrow-right" size={14} />
                  </ButtonLink>
                </li>
              );
            })}
          </ol>
        </Card>

        <Card className={styles.missionCard}>
          <div className={styles.missionTopRow}>
            <div className={styles.missionHeading}>
              <span className={styles.cardEyebrow}>
                <Icon name="target" size={12} />
                Recommended next
              </span>
              <h2 className={styles.missionTitle}>{mission.title}</h2>
              <p className={styles.muted}>{mission.missionLabel}</p>
            </div>
            <span
              className={styles.difficultyPill}
              style={{ ["--pill-color" as string]: missionDifficulty.color }}
            >
              <span className={styles.difficultyDot} aria-hidden="true" />
              {missionDifficulty.label}
            </span>
          </div>

          <div className={styles.filterRow}>
            <div className={styles.filterGroup}>
              <label className={styles.label} htmlFor="theme-filter">
                <Icon name="compass" size={14} />
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
            <div className={styles.filterGroup}>
              <label className={styles.label} htmlFor="difficulty-filter">
                <Icon name="filter" size={14} />
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
          </div>

          {mission.skillTags.length > 0 ? (
            <div className={styles.chipRow}>
              {mission.skillTags.map((skill) => (
                <Tag key={skill}>{skill}</Tag>
              ))}
            </div>
          ) : null}

          <ButtonLink href={`/activity/${mission.activityId}`}>
            <Icon name="play" size={16} />
            Start mission
          </ButtonLink>
          {dashboard?.recommendation ? (
            <div className={styles.recommendationReason}>
              <strong>Why this mission?</strong>
              <span>{dashboard.recommendation.reason}</span>
              <small>{dashboard.recommendation.rule}</small>
            </div>
          ) : null}
        </Card>

        <Split>
          <Card as="article" className={styles.cardWithHeader}>
            <div className={styles.cardHeader}>
              <span className={styles.cardIcon} style={{ ["--icon-color" as string]: "var(--warning)" }}>
                <Icon name="trophy" size={18} />
              </span>
              <h3>Reward tracker</h3>
            </div>
            <StatGrid>
              <div className={styles.stat}>
                <span className={styles.statTopRow}>
                  <Icon name="star" size={14} />
                  <span className={styles.statLabel}>Stars</span>
                </span>
                <p className={styles.statValue}>{rewards.stars}</p>
              </div>
              <div className={styles.stat}>
                <span className={styles.statTopRow}>
                  <Icon name="sparkles" size={14} />
                  <span className={styles.statLabel}>Points</span>
                </span>
                <p className={styles.statValue}>{points}</p>
              </div>
              <div className={styles.stat}>
                <span className={styles.statTopRow}>
                  <Icon name="flame" size={14} />
                  <span className={styles.statLabel}>Streak</span>
                </span>
                <p className={styles.statValue}>{rewards.streakDays}d</p>
              </div>
            </StatGrid>
            {rewards.badges.length > 0 ? (
              <div className={styles.chipRow}>
                {rewards.badges.map((badge) => (
                  <Tag key={badge}>
                    <Icon name="award" size={11} />
                    {badge}
                  </Tag>
                ))}
              </div>
            ) : null}
          </Card>

          <Card as="article" className={styles.cardWithHeader}>
            <div className={styles.cardHeader}>
              <span className={styles.cardIcon} style={{ ["--icon-color" as string]: "var(--success)" }}>
                <Icon name="check-circle" size={18} />
              </span>
              <h3>Recent practice</h3>
            </div>
            <ul className={styles.sessionList}>
              {recent.length === 0 ? (
                <li className={styles.emptyHint}>
                  No sessions yet. Start today&apos;s quest to begin your streak.
                </li>
              ) : null}
              {recent.map((session) => (
                <li key={session.id} className={styles.sessionItem}>
                  <span className={styles.sessionTitle}>{session.activityTitle}</span>
                  <span className={styles.sessionScore}>{session.scoreLabel}</span>
                </li>
              ))}
            </ul>
          </Card>

          <Card as="article" className={styles.cardWithHeader}>
            <div className={styles.cardHeader}>
              <span className={styles.cardIcon} style={{ ["--icon-color" as string]: "var(--brand)" }}>
                <Icon name="book" size={18} />
              </span>
              <h3>Available activities</h3>
            </div>
            <ul className={styles.activityList}>
              {availableActivities.length === 0 ? (
                <li className={styles.emptyHint}>No activities available yet.</li>
              ) : null}
              {availableActivities.map((item) => {
                const meta = DIFFICULTY_META[item.difficulty];
                const isCurrent = selectedActivityId === item.id;
                return (
                  <li
                    key={item.id}
                    className={`${styles.activityItem} ${isCurrent ? styles.activityItemActive : ""}`}
                  >
                    <div className={styles.activityInfo}>
                      <div className={styles.activityTitleRow}>
                        <strong>{item.title}</strong>
                        {isCurrent ? <span className={styles.activeBadge}>Current</span> : null}
                      </div>
                      <div className={styles.activityMeta}>
                        <span>
                          <Icon name="compass" size={12} />
                          {item.theme}
                        </span>
                        <span
                          className={styles.metaPill}
                          style={{ ["--pill-color" as string]: meta.color }}
                        >
                          <span className={styles.difficultyDot} aria-hidden="true" />
                          {meta.label}
                        </span>
                      </div>
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
                        <Icon name="arrow-right" size={14} />
                      </ButtonLink>
                    </div>
                  </li>
                );
              })}
            </ul>
          </Card>
        </Split>
      </Stack>
    </AppShell>
  );
}

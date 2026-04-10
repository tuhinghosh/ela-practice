"use client";

import { useEffect, useState } from "react";

import { AppShell } from "@/components/app-shell";
import { ButtonLink } from "@/components/button";
import { Card } from "@/components/card";
import { Split, Stack, StatGrid } from "@/components/layout";
import { Tag } from "@/components/tag";
import { ApiError, type ActivitiesResponse, type DashboardResponse, getDashboard, listActivities } from "@/lib/api";
import { activities as fallbackActivities, recentSessions, rewardSnapshot } from "@/lib/mock-data";

import styles from "./screens.module.css";

export default function Home() {
  const [dashboard, setDashboard] = useState<DashboardResponse | null>(null);
  const [activityList, setActivityList] = useState<ActivitiesResponse["activities"]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    const run = async () => {
      try {
        const payload = await getDashboard();
        setDashboard(payload);
        const activitiesPayload = await listActivities();
        setActivityList(activitiesPayload.activities);
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

  const fallbackMission = fallbackActivities[0];
  const baseMission = dashboard
    ? {
        activityId: dashboard.mission.activity_id,
        missionLabel: dashboard.mission.mission_label,
        skillTags: dashboard.mission.skill_tags,
      }
    : {
        activityId: fallbackMission.id,
        missionLabel: fallbackMission.missionLabel,
        skillTags: fallbackMission.skillTags,
      };
  const suggestedActivityId = typeof window !== "undefined" ? localStorage.getItem("ela:suggested-activity") : null;
  const suggestedActivity = (activityList.length > 0 ? activityList : fallbackActivities).find(
    (activity) => activity.id === suggestedActivityId,
  );
  const mission = suggestedActivity
    ? {
        activityId: suggestedActivity.id,
        missionLabel: `Coach quest unlocked: ${suggestedActivity.title}`,
        skillTags: ["coach-suggested", ...(dashboard?.progress.growth_areas ?? []).slice(0, 2)],
      }
    : baseMission;

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
          <p className={styles.muted}>{mission.missionLabel}</p>
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
            <ul className={styles.list}>
              {(activityList.length > 0
                ? activityList.map((item) => ({
                    id: item.id,
                    label: item.title,
                  }))
                : fallbackActivities.map((item) => ({ id: item.id, label: item.title }))
              ).length === 0 ? <li>No activities available yet.</li> : null}
              {(activityList.length > 0
                ? activityList.map((item) => ({
                    id: item.id,
                    label: item.title,
                  }))
                : fallbackActivities.map((item) => ({ id: item.id, label: item.title }))
              ).map((item) => (
                <li key={item.id}>{item.label}</li>
              ))}
            </ul>
          </Card>
        </Split>
      </Stack>
    </AppShell>
  );
}

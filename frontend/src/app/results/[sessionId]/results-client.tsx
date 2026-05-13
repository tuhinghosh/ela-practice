"use client";

import { useSearchParams } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";

import { AICoachPanel } from "@/components/ai-coach-panel";
import { AppShell } from "@/components/app-shell";
import { ButtonLink } from "@/components/button";
import { Card } from "@/components/card";
import { Icon } from "@/components/icon";
import { Split } from "@/components/layout";
import { ApiError, getAICoachFeedback, getSessionResult, type AICoachResponse, type SessionResultResponse } from "@/lib/api";
import { coachSample, recentSessions } from "@/lib/mock-data";

import styles from "../../screens.module.css";

type Props = {
  initialSessionId: string;
};

function cleanText(value: string | null | undefined, fallback: string): string {
  if (typeof value !== "string") return fallback;
  const trimmed = value.trim();
  return trimmed.length > 0 ? trimmed : fallback;
}

function normalizeCoachPayload(payload: AICoachResponse): AICoachResponse {
  return {
    ...payload,
    message_to_child: cleanText(
      payload.message_to_child,
      "Great effort. Keep using details from the passage to support your ideas.",
    ),
    celebration: cleanText(payload.celebration, "Nice work finishing this activity."),
    explanation: cleanText(payload.explanation, "Your strongest answers use clear evidence from the text."),
    hint: payload.hint ? cleanText(payload.hint, "") : payload.hint,
    writing_feedback: payload.writing_feedback ? cleanText(payload.writing_feedback, "") : payload.writing_feedback,
  };
}

function ScoreRing({ percent }: { percent: number }) {
  const radius = 42;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (percent / 100) * circumference;
  return (
    <div className={styles.scoreCircle}>
      <svg width="96" height="96" viewBox="0 0 96 96" aria-hidden="true">
        <defs>
          <linearGradient id="scoreGrad" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0%" stopColor="#5b6bff" />
            <stop offset="100%" stopColor="#8b5cf6" />
          </linearGradient>
        </defs>
        <circle cx="48" cy="48" r={radius} stroke="#e2e6f5" strokeWidth="8" fill="none" />
        <circle
          cx="48"
          cy="48"
          r={radius}
          stroke="url(#scoreGrad)"
          strokeWidth="8"
          fill="none"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          strokeLinecap="round"
        />
      </svg>
      <span className={styles.scoreCircleValue}>{Math.round(percent)}%</span>
    </div>
  );
}

export default function ResultsClient({ initialSessionId }: Props) {
  const searchParams = useSearchParams();
  const querySessionId = searchParams.get("session");
  const sessionId = querySessionId ?? initialSessionId;

  const fallback = useMemo(
    () => recentSessions.find((item) => item.id === initialSessionId) ?? recentSessions[0],
    [initialSessionId],
  );
  const [result, setResult] = useState<SessionResultResponse | null>(null);
  const [error, setError] = useState("");
  const [coach, setCoach] = useState<AICoachResponse | null>(null);
  const [coachQuestion, setCoachQuestion] = useState("");
  const [lastAskedQuestion, setLastAskedQuestion] = useState("");
  const [coachError, setCoachError] = useState("");
  const [isAskingCoach, setIsAskingCoach] = useState(false);

  useEffect(() => {
    const run = async () => {
      try {
        const payload = await getSessionResult(sessionId);
        setResult(payload);
      } catch (err) {
        if (err instanceof ApiError && err.status === 401) {
          window.location.href = "/login";
          return;
        }
        setError("Could not load live result details. Showing local preview.");
      }
    };
    void run();
  }, [sessionId]);

  const requestCoach = useCallback(async (question?: string) => {
    if (!result) return;
    const normalizedQuestion = (question ?? "").trim();
    setIsAskingCoach(true);
    setCoachError("");
    if (normalizedQuestion) {
      setLastAskedQuestion(normalizedQuestion);
    }
    try {
      const payload = await getAICoachFeedback(result.session_id, normalizedQuestion || undefined);
      setCoach(normalizeCoachPayload(payload));
      if (payload.suggested_next_activity_id) {
        localStorage.setItem("ela:suggested-activity", payload.suggested_next_activity_id);
      }
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        window.location.href = "/login";
        return;
      }
      setCoachError("Coach is temporarily unavailable. You can continue your quest and try again soon.");
    } finally {
      setIsAskingCoach(false);
    }
  }, [result]);

  useEffect(() => {
    if (!result) return;
    void requestCoach();
  }, [result, requestCoach]);

  const resolved = result
    ? {
        activityTitle: result.activity_title,
        scorePercent: result.score_percent,
        scoreLabel: `${Math.round(result.score_percent)}%`,
        skillLabel: Object.keys(result.skill_breakdown)[0] ?? "reading-comprehension",
        sessionId: result.session_id,
        rubric: result.rubric,
        rewardSnapshot: result.reward_snapshot,
      }
    : {
        activityTitle: fallback.activityTitle,
        scorePercent: parseInt(fallback.scoreLabel, 10) || 0,
        scoreLabel: fallback.scoreLabel,
        skillLabel: fallback.skill,
        sessionId: fallback.id,
        rubric: null,
        rewardSnapshot: null,
      };

  return (
    <AppShell
      title={`Results: ${resolved.activityTitle}`}
      subtitle="You finished this quest. Celebrate your progress and ask the coach one focused follow-up question."
      eyebrow="Quest complete"
      heroIcon="trophy"
    >
      {error ? (
        <p role="alert" className={styles.error}>
          <Icon name="message-circle" size={16} />
          {error} Your progress is still saved.
        </p>
      ) : null}
      <Split>
        <Card>
          <div className={styles.cardHeader}>
            <span className={styles.cardIcon} style={{ ["--icon-color" as string]: "var(--brand)" }}>
              <Icon name="target" size={18} />
            </span>
            <h2>Score snapshot</h2>
          </div>
          <p className={styles.muted}>Session ID: {resolved.sessionId}</p>
          <div className={styles.scoreCircleWrap}>
            <ScoreRing percent={resolved.scorePercent} />
            <div className={styles.scoreMeta}>
              <span className={styles.scoreFocus}>
                <Icon name="target" size={14} />
                {resolved.skillLabel}
              </span>
              <p className={styles.muted}>Your focus skill for this quest.</p>
            </div>
          </div>
          {resolved.rubric ? (
            <ul className={styles.rubricList}>
              <li className={styles.rubricRow}>
                <span className={styles.rubricLabel}>
                  <Icon name="check-circle" size={14} />
                  Completion
                </span>
                <span className={styles.rubricValue}>{resolved.rubric.completion}</span>
              </li>
              <li className={styles.rubricRow}>
                <span className={styles.rubricLabel}>
                  <Icon name="target" size={14} />
                  Relevance
                </span>
                <span className={styles.rubricValue}>{resolved.rubric.relevance}</span>
              </li>
              <li className={styles.rubricRow}>
                <span className={styles.rubricLabel}>
                  <Icon name="pencil" size={14} />
                  Sentence completeness
                </span>
                <span className={styles.rubricValue}>{resolved.rubric.sentence_completeness}</span>
              </li>
            </ul>
          ) : null}
        </Card>

        <Card>
          <div className={styles.cardHeader}>
            <span className={styles.cardIcon} style={{ ["--icon-color" as string]: "var(--warning)" }}>
              <Icon name="trophy" size={18} />
            </span>
            <h2>Quest celebration</h2>
          </div>
          {resolved.rewardSnapshot ? (
            <>
              <div className={styles.rewardCallout}>
                <span className={styles.rewardIcon} aria-hidden="true">
                  <Icon name="star" size={20} />
                </span>
                <div>
                  <p>
                    Awesome work! You earned <strong>+{resolved.rewardSnapshot.stars_earned} stars</strong> and{" "}
                    <strong>+{resolved.rewardSnapshot.points_earned} points</strong>.
                  </p>
                  <p>
                    Streak: {resolved.rewardSnapshot.streak_after} day(s), Total points:{" "}
                    {resolved.rewardSnapshot.total_points}
                  </p>
                </div>
              </div>
              {resolved.rewardSnapshot.new_badges.length > 0 ? (
                <p className={styles.muted}>
                  <span className={styles.badgePop}>
                    <Icon name="award" size={12} />
                    New badge unlocked: {resolved.rewardSnapshot.new_badges.join(", ")}.
                  </span>
                </p>
              ) : null}
            </>
          ) : (
            <p className={styles.muted}>Great effort. Keep your reading adventure streak going!</p>
          )}
          <h3>Coach feedback</h3>
          <p className={styles.muted}>
            {coach?.message_to_child ?? coachSample.celebration}
          </p>
          {coach?.celebration ? (
            <p className={styles.muted}>
              <strong>{coach.celebration}</strong>
            </p>
          ) : null}
          <ButtonLink href="/" tone="secondary">
            <Icon name="home" size={16} />
            Back to mission home
          </ButtonLink>
        </Card>
        <AICoachPanel
          coach={coach}
          question={coachQuestion}
          lastAskedQuestion={lastAskedQuestion}
          onQuestionChange={setCoachQuestion}
          onAskCoach={() => void requestCoach(coachQuestion.trim())}
          isAsking={isAskingCoach}
          error={coachError}
        />
      </Split>
    </AppShell>
  );
}

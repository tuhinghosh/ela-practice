"use client";

import { useSearchParams } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";

import { AICoachPanel } from "@/components/ai-coach-panel";
import { AppShell } from "@/components/app-shell";
import { ButtonLink } from "@/components/button";
import { Card } from "@/components/card";
import { Split, StatGrid } from "@/components/layout";
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
        scoreLabel: `${Math.round(result.score_percent)}%`,
        skillLabel: Object.keys(result.skill_breakdown)[0] ?? "reading-comprehension",
        sessionId: result.session_id,
        rubric: result.rubric,
        rewardSnapshot: result.reward_snapshot,
      }
    : {
        activityTitle: fallback.activityTitle,
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
    >
      {error ? (
        <p role="alert" className={styles.error}>
          {error} Your progress is still saved.
        </p>
      ) : null}
      <Split>
        <Card>
          <h2>Score snapshot</h2>
          <p className={styles.muted}>Session ID: {resolved.sessionId}</p>
          <StatGrid>
            <div className={styles.stat}>
              <span className={styles.statLabel}>Score</span>
              <p className={styles.statValue}>{resolved.scoreLabel}</p>
            </div>
            <div className={styles.stat}>
              <span className={styles.statLabel}>Focus skill</span>
              <p className={styles.statValue}>{resolved.skillLabel}</p>
            </div>
          </StatGrid>
          {resolved.rubric ? (
            <ul className={styles.list}>
              <li>Completion: {resolved.rubric.completion}</li>
              <li>Relevance: {resolved.rubric.relevance}</li>
              <li>Sentence completeness: {resolved.rubric.sentence_completeness}</li>
            </ul>
          ) : null}
        </Card>

        <Card>
          <h2>Quest celebration</h2>
          {resolved.rewardSnapshot ? (
            <>
              <p className={styles.muted}>
                Awesome work! You earned <strong>+{resolved.rewardSnapshot.stars_earned} stars</strong> and{" "}
                <strong>+{resolved.rewardSnapshot.points_earned} points</strong>.
              </p>
              <p className={styles.muted}>
                Streak: {resolved.rewardSnapshot.streak_after} day(s), Total points:{" "}
                {resolved.rewardSnapshot.total_points}
              </p>
              {resolved.rewardSnapshot.new_badges.length > 0 ? (
                <p className={styles.muted}>New badge unlocked: {resolved.rewardSnapshot.new_badges.join(", ")}.</p>
              ) : null}
            </>
          ) : (
            <p className={styles.muted}>Great effort. Keep your reading adventure streak going!</p>
          )}
          <h3>Coach feedback (post-submission)</h3>
          <p className={styles.muted}>
            {coach?.message_to_child ?? coach?.celebration ?? coachSample.celebration}
          </p>
          <p className={styles.muted}>{coach?.explanation ?? coachSample.explanation}</p>
          <p className={styles.muted}>{coach?.hint ?? coachSample.nextStepSuggestion}</p>
          <ButtonLink href="/" tone="secondary">
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

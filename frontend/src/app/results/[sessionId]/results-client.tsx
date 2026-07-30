"use client";

import { useSearchParams } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";

import { AICoachPanel } from "@/components/ai-coach-panel";
import { AppShell } from "@/components/app-shell";
import { Button, ButtonLink } from "@/components/button";
import { Card } from "@/components/card";
import { Icon } from "@/components/icon";
import { Split } from "@/components/layout";
import { Tag } from "@/components/tag";
import { ApiError, getAICoachFeedback, getSessionResult, recordSessionReaction, type AICoachResponse, type SessionResultResponse } from "@/lib/api";
import { coachSample, recentSessions } from "@/lib/mock-data";

import styles from "../../screens.module.css";

type Props = {
  initialSessionId: string;
};

const REYANA_MISSION_IDS = [
  "pilot-mystery-cat-01",
  "pilot-space-mars-01",
  "pilot-world-japan-01",
] as const;

const REYANA_MISSION_TITLES: Record<(typeof REYANA_MISSION_IDS)[number], string> = {
  "pilot-mystery-cat-01": "A Day Called a Sol",
  "pilot-space-mars-01": "Japan: One Country, Many Islands",
  "pilot-world-japan-01": "Mission Home",
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

function formatSkill(skill: string): string {
  return skill
    .split("-")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
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
  const [reaction, setReaction] = useState<"fun" | "okay" | "confusing" | null>(null);
  const [reactionError, setReactionError] = useState("");

  const chooseReaction = async (value: "fun" | "okay" | "confusing") => {
    if (!result) return;
    setReactionError("");
    try {
      await recordSessionReaction(result.session_id, value);
      setReaction(value);
    } catch {
      setReactionError("Could not save that reaction. Please try again.");
    }
  };

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
        questionResults: result.question_results ?? [],
      }
    : {
        activityTitle: fallback.activityTitle,
        scorePercent: parseInt(fallback.scoreLabel, 10) || 0,
        scoreLabel: fallback.scoreLabel,
        skillLabel: fallback.skill,
        sessionId: fallback.id,
        rubric: null,
        rewardSnapshot: null,
        questionResults: [],
      };

  const pilotIndex = result ? REYANA_MISSION_IDS.indexOf(result.activity_id as (typeof REYANA_MISSION_IDS)[number]) : -1;
  const nextPilotId = pilotIndex >= 0 ? REYANA_MISSION_IDS[pilotIndex + 1] : undefined;
  const nextDestination = nextPilotId ? `/activity/${nextPilotId}` : "/";
  const nextLabel = nextPilotId ? `Next: ${REYANA_MISSION_TITLES[result!.activity_id as (typeof REYANA_MISSION_IDS)[number]]}` : "Back to mission home";

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
      <Card className={styles.resultReviewCard}>
        <div className={styles.cardHeader}>
          <span className={styles.cardIcon} style={{ ["--icon-color" as string]: "var(--brand)" }}>
            <Icon name="target" size={18} />
          </span>
          <div>
            <h2>Skills from this mission</h2>
            <p className={styles.muted}>Each score comes from the question that measured that skill.</p>
          </div>
        </div>
        <div className={styles.skillResultGrid}>
          {Object.entries(result?.skill_breakdown ?? {}).map(([skill, score]) => (
            <div key={skill} className={styles.skillResult}>
              <span>{formatSkill(skill)}</span>
              <strong>{Math.round(score)}%</strong>
            </div>
          ))}
          {!result ? <p className={styles.muted}>Skill details will appear with live results.</p> : null}
        </div>
      </Card>

      {resolved.questionResults.length > 0 ? (
        <Card className={styles.resultReviewCard}>
          <div className={styles.cardHeader}>
            <span className={styles.cardIcon} style={{ ["--icon-color" as string]: "var(--success)" }}>
              <Icon name="check-circle" size={18} />
            </span>
            <div>
              <h2>Review your answers</h2>
              <p className={styles.muted}>Use the explanation to see which passage clue matters.</p>
            </div>
          </div>
          <ol className={styles.answerReviewList}>
            {resolved.questionResults.map((question, index) => (
              <li key={question.question_id} className={styles.answerReviewItem}>
                <div className={styles.answerReviewHeading}>
                  <span className={styles.questionNumber}>Q{index + 1}</span>
                  <Tag>{formatSkill(question.skill_tag)}</Tag>
                  <span
                    className={`${styles.answerStatus} ${
                      question.is_correct === true
                        ? styles.answerCorrect
                        : question.is_correct === false
                          ? styles.answerNeedsReview
                          : styles.answerWritten
                    }`}
                  >
                    {question.is_correct === true
                      ? "Correct"
                      : question.is_correct === false
                        ? "Review this one"
                        : "Written response"}
                  </span>
                </div>
                <p className={styles.answerPrompt}>{question.prompt}</p>
                <div className={styles.answerDetailGrid}>
                  <div>
                    <span className={styles.answerLabel}>Your answer</span>
                    <p>{question.child_answer}</p>
                  </div>
                  {question.is_correct === false && question.correct_answer ? (
                    <div>
                      <span className={styles.answerLabel}>Best answer</span>
                      <p>{question.correct_answer}</p>
                    </div>
                  ) : null}
                </div>
                <p className={styles.answerExplanation}>
                  <Icon name="book" size={15} />
                  <span>{question.explanation}</span>
                </p>
              </li>
            ))}
          </ol>
        </Card>
      ) : null}
      {result ? (
        <Card>
          <div className={styles.cardHeader}>
            <span className={styles.cardIcon} style={{ ["--icon-color" as string]: "var(--accent)" }}>
              <Icon name="message-circle" size={18} />
            </span>
            <div>
              <h2>How did this mission feel?</h2>
              <p className={styles.muted}>One quick tap helps choose and improve future missions.</p>
            </div>
          </div>
          <div className={styles.chipRow} aria-label="Activity reaction">
            {(["fun", "okay", "confusing"] as const).map((value) => (
              <Button
                key={value}
                type="button"
                tone={reaction === value ? "primary" : "secondary"}
                onClick={() => void chooseReaction(value)}
              >
                {value === "fun" ? "Fun" : value === "okay" ? "Okay" : "Confusing"}
              </Button>
            ))}
          </div>
          {reaction ? <p role="status">Saved: {reaction}.</p> : null}
          {reactionError ? <p role="alert" className={styles.error}>{reactionError}</p> : null}
        </Card>
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
          <ButtonLink href={nextDestination} tone={nextPilotId ? "primary" : "secondary"}>
            <Icon name={nextPilotId ? "arrow-right" : "home"} size={16} />
            {nextLabel}
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

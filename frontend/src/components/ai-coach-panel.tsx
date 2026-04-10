"use client";

import { Button, ButtonLink } from "@/components/button";
import { Card } from "@/components/card";
import type { AICoachResponse } from "@/lib/api";

import styles from "@/app/screens.module.css";

type Props = {
  coach: AICoachResponse | null;
  question: string;
  onQuestionChange: (value: string) => void;
  onAskCoach: () => void;
  isAsking: boolean;
  error: string;
};

export function AICoachPanel({ coach, question, onQuestionChange, onAskCoach, isAsking, error }: Props) {
  return (
    <Card>
      <h2>AI Coach Corner</h2>
      <p className={styles.muted}>
        Ask a short question about this completed activity. The coach helps after submission only.
      </p>

      {coach ? (
        <>
          <p className={styles.muted}>{coach.celebration}</p>
          <p className={styles.muted}>{coach.explanation}</p>
          {coach.hint ? <p className={styles.muted}>Hint: {coach.hint}</p> : null}
          {coach.writing_feedback ? <p className={styles.muted}>Writing feedback: {coach.writing_feedback}</p> : null}
          {coach.suggested_next_activity_id ? (
            <ButtonLink href={`/activity/${coach.suggested_next_activity_id}`} tone="ghost">
              Try coach suggestion
            </ButtonLink>
          ) : null}
        </>
      ) : (
        <p className={styles.muted}>Loading coach feedback...</p>
      )}

      <label htmlFor="coach-question" className={styles.label}>
        Ask the coach about this activity
      </label>
      <textarea
        id="coach-question"
        className={styles.textarea}
        maxLength={220}
        value={question}
        onChange={(event) => onQuestionChange(event.target.value)}
        placeholder="Example: How can I make my evidence sentence stronger?"
      />
      <Button type="button" onClick={onAskCoach} disabled={isAsking}>
        {isAsking ? "Coach is thinking..." : "Ask coach"}
      </Button>

      {error ? (
        <p role="alert" className={styles.error}>
          {error}
        </p>
      ) : null}
    </Card>
  );
}

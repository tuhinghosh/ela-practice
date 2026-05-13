"use client";

import { Button, ButtonLink } from "@/components/button";
import { Card } from "@/components/card";
import { Icon } from "@/components/icon";
import type { AICoachResponse } from "@/lib/api";

import coachStyles from "./ai-coach-panel.module.css";
import styles from "@/app/screens.module.css";

type Props = {
  coach: AICoachResponse | null;
  question: string;
  lastAskedQuestion: string;
  onQuestionChange: (value: string) => void;
  onAskCoach: () => void;
  isAsking: boolean;
  error: string;
};

export function AICoachPanel({
  coach,
  question,
  lastAskedQuestion,
  onQuestionChange,
  onAskCoach,
  isAsking,
  error,
}: Props) {
  return (
    <Card>
      <div className={coachStyles.header}>
        <span className={coachStyles.iconWrap} aria-hidden="true">
          <Icon name="sparkles" size={20} />
        </span>
        <div className={coachStyles.headerText}>
          <h2 className={coachStyles.title}>Reading Coach</h2>
          <p className={coachStyles.headerSub}>Friendly, personalized tips on your work</p>
        </div>
      </div>

      {coach ? (
        <div className={coachStyles.feedbackArea}>
          {lastAskedQuestion ? (
            <div className={coachStyles.questionBubble}>
              <span className={coachStyles.bubbleLabel}>
                <Icon name="message-circle" size={12} />
                You asked:
              </span>{" "}
              {lastAskedQuestion}
            </div>
          ) : null}

          <div className={coachStyles.feedbackCard}>
            <p className={coachStyles.feedbackText}>{coach.message_to_child}</p>
          </div>

          {coach.hint ? (
            <div className={coachStyles.tipCard}>
              <span className={coachStyles.tipIcon} aria-hidden="true">
                <Icon name="lightbulb" size={18} />
              </span>
              <div>
                <span className={coachStyles.cardLabel}>Try this next time</span>
                <p className={coachStyles.cardText}>{coach.hint}</p>
              </div>
            </div>
          ) : null}

          {coach.writing_feedback ? (
            <div className={coachStyles.writingCard}>
              <span className={coachStyles.writingIcon} aria-hidden="true">
                <Icon name="pencil" size={18} />
              </span>
              <div>
                <span className={coachStyles.cardLabel}>About your writing</span>
                <p className={coachStyles.cardText}>{coach.writing_feedback}</p>
              </div>
            </div>
          ) : null}

          {coach.suggested_next_activity_id ? (
            <ButtonLink href={`/activity/${coach.suggested_next_activity_id}`} tone="ghost">
              <Icon name="arrow-right" size={14} />
              Try the next challenge
            </ButtonLink>
          ) : null}
        </div>
      ) : (
        <div className={coachStyles.loading}>
          <span className={coachStyles.loadingDot} />
          <span className={coachStyles.loadingDot} />
          <span className={coachStyles.loadingDot} />
          <span className={coachStyles.loadingText}>Coach is reading your answers...</span>
        </div>
      )}

      <div className={coachStyles.askSection}>
        <label htmlFor="coach-question" className={coachStyles.askLabel}>
          <Icon name="message-circle" size={14} />
          Ask the coach a question about this activity
        </label>
        <textarea
          id="coach-question"
          className={coachStyles.askInput}
          maxLength={220}
          rows={2}
          value={question}
          onChange={(event) => onQuestionChange(event.target.value)}
          placeholder="Example: Can you show me what a strong answer looks like?"
        />
        <Button type="button" onClick={onAskCoach} disabled={isAsking}>
          {isAsking ? "Coach is thinking..." : (
            <>
              <Icon name="sparkles" size={14} />
              Ask coach
            </>
          )}
        </Button>
      </div>

      {error ? (
        <p role="alert" className={styles.error}>
          <Icon name="message-circle" size={16} />
          {error}
        </p>
      ) : null}
    </Card>
  );
}

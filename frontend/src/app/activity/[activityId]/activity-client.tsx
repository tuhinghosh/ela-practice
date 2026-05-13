"use client";

import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

import { AppShell } from "@/components/app-shell";
import { Button } from "@/components/button";
import { Card } from "@/components/card";
import { Icon } from "@/components/icon";
import { Tag } from "@/components/tag";
import { ApiError, getActivity, submitActivity, type ActivityDetailResponse } from "@/lib/api";
import { activities } from "@/lib/mock-data";

import styles from "../../screens.module.css";

type Props = {
  activityId: string;
};

const DIFFICULTY_COLOR: Record<string, string> = {
  easy: "var(--success)",
  medium: "var(--warning)",
  difficult: "var(--danger)",
};

export default function ActivityClient({ activityId }: Props) {
  const router = useRouter();
  const fallback = useMemo(() => activities.find((item) => item.id === activityId) ?? activities[0], [activityId]);
  const [activity, setActivity] = useState<ActivityDetailResponse | null>(null);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [error, setError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [usingFallback, setUsingFallback] = useState(false);

  useEffect(() => {
    const run = async () => {
      try {
        const payload = await getActivity(activityId);
        setActivity(payload);
      } catch (err) {
        if (err instanceof ApiError && err.status === 401) {
          window.location.href = "/login";
          return;
        }
        setError("Could not connect to the server. Please try again later.");
        setUsingFallback(true);
      }
    };
    void run();
  }, [activityId]);

  const resolved = activity ?? {
    id: fallback.id,
    title: fallback.title,
    difficulty: fallback.difficulty,
    passage_type: fallback.passageType,
    mission_label: fallback.missionLabel,
    passage_title: fallback.passageTitle,
    passage_text: fallback.passageText,
    skill_tags: fallback.skillTags,
    questions: fallback.questions,
  };
  const difficultyLabel = (resolved.difficulty ?? "medium").toUpperCase();
  const difficultyColor = DIFFICULTY_COLOR[resolved.difficulty ?? "medium"] ?? "var(--brand)";
  const passageParagraphs = resolved.passage_text
    .split(/\n\s*\n/)
    .map((paragraph) => paragraph.trim())
    .filter((paragraph) => paragraph.length > 0);

  const totalQuestions = resolved.questions.length;
  const answeredCount = resolved.questions.filter(
    (question) => answers[question.id] !== undefined && answers[question.id].trim() !== "",
  ).length;
  const allAnswered = answeredCount === totalQuestions;
  const progressPercent = totalQuestions > 0 ? Math.round((answeredCount / totalQuestions) * 100) : 0;

  const onSubmit = async () => {
    if (!allAnswered) {
      setError("Please answer all questions before submitting.");
      return;
    }
    setIsSubmitting(true);
    setError("");
    try {
      const payload = {
        responses: resolved.questions.map((question) =>
          question.type === "multiple-choice"
            ? { question_id: question.id, answer_choice: answers[question.id] }
            : { question_id: question.id, answer_text: answers[question.id] },
        ),
      };
      const result = await submitActivity(resolved.id, payload);
      router.push(`/results/session-001?session=${encodeURIComponent(result.session_id)}`);
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        window.location.href = "/login";
        return;
      }
      if (err instanceof ApiError && err.status === 422) {
        setError(err.message);
      } else {
        setError("Could not submit answers. Please try again.");
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <AppShell
      title={resolved.title}
      subtitle={`${resolved.passage_type} passage`}
      eyebrow="Reading activity"
      heroIcon="book"
    >
      {error ? (
        <p role="alert" className={styles.error}>
          <Icon name="message-circle" size={16} />
          {error}
        </p>
      ) : null}
      <Card>
        <div className={styles.cardHeader}>
          <span className={styles.cardIcon} style={{ ["--icon-color" as string]: "var(--brand)" }}>
            <Icon name="book" size={18} />
          </span>
          <h2>{resolved.passage_title}</h2>
        </div>
        <div className={styles.chipRow}>
          <span
            className={styles.difficultyPill}
            style={{ ["--pill-color" as string]: difficultyColor }}
          >
            <span className={styles.difficultyDot} aria-hidden="true" />
            Difficulty: {difficultyLabel}
          </span>
          {resolved.skill_tags?.slice(0, 3).map((skill) => (
            <Tag key={skill}>{skill}</Tag>
          ))}
        </div>
        <div className={styles.passage}>
          {(passageParagraphs.length > 0 ? passageParagraphs : [resolved.passage_text]).map((paragraph, index) => (
            <p key={`passage-paragraph-${index}`} className={styles.passageParagraph}>
              {paragraph}
            </p>
          ))}
        </div>
      </Card>

      <Card>
        <div className={styles.cardHeader}>
          <span className={styles.cardIcon} style={{ ["--icon-color" as string]: "var(--accent)" }}>
            <Icon name="clipboard-list" size={18} />
          </span>
          <h2>Questions</h2>
        </div>
        <div className={styles.progressRow}>
          <span className={styles.progressLabel}>
            <Icon name="target" size={14} />
            Progress
          </span>
          <span>
            {answeredCount} of {totalQuestions} answered
          </span>
        </div>
        <div className={styles.progressTrack} role="progressbar" aria-valuenow={progressPercent} aria-valuemin={0} aria-valuemax={100}>
          <span className={styles.progressFill} style={{ width: `${progressPercent}%` }} />
        </div>
        {resolved.questions.map((question, index) => (
          <article key={question.id} className={styles.question}>
            <div className={styles.questionNumberRow}>
              <span className={styles.questionNumber}>Q{index + 1}</span>
              <span className={styles.questionType}>
                {question.type === "multiple-choice" ? (
                  <>
                    <Icon name="check-circle" size={12} />
                    Multiple choice
                  </>
                ) : (
                  <>
                    <Icon name="pencil" size={12} />
                    Short response
                  </>
                )}
              </span>
            </div>
            <p>{question.prompt}</p>
            {question.type === "multiple-choice" ? (
              <div className={styles.choiceList}>
                {question.choices?.map((choice) => (
                  <label key={choice} className={styles.choiceLabel}>
                    <input
                      type="radio"
                      name={question.id}
                      value={choice}
                      checked={answers[question.id] === choice}
                      onChange={(event) =>
                        setAnswers((current) => ({
                          ...current,
                          [question.id]: event.target.value,
                        }))
                      }
                    />
                    {choice}
                  </label>
                ))}
              </div>
            ) : (
              <textarea
                className={styles.textarea}
                value={answers[question.id] ?? ""}
                placeholder="Type your short response here..."
                onChange={(event) =>
                  setAnswers((current) => ({
                    ...current,
                    [question.id]: event.target.value,
                  }))
                }
                aria-label="Short response input"
              />
            )}
          </article>
        ))}
        <Button type="button" onClick={onSubmit} disabled={isSubmitting || usingFallback || !allAnswered}>
          {isSubmitting ? (
            "Submitting..."
          ) : usingFallback ? (
            "Server unavailable"
          ) : (
            <>
              <Icon name="check-circle" size={16} />
              Submit answers
            </>
          )}
        </Button>
      </Card>
    </AppShell>
  );
}

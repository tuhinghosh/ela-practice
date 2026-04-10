"use client";

import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

import { AppShell } from "@/components/app-shell";
import { Button } from "@/components/button";
import { Card } from "@/components/card";
import { Tag } from "@/components/tag";
import { ApiError, getActivity, submitActivity, type ActivityDetailResponse } from "@/lib/api";
import { activities } from "@/lib/mock-data";

import styles from "../../screens.module.css";

type Props = {
  activityId: string;
};

export default function ActivityClient({ activityId }: Props) {
  const router = useRouter();
  const fallback = useMemo(() => activities.find((item) => item.id === activityId) ?? activities[0], [activityId]);
  const [activity, setActivity] = useState<ActivityDetailResponse | null>(null);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [error, setError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

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
        setError("Could not load live activity data. Showing local preview data.");
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

  const onSubmit = async () => {
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
    <AppShell title={resolved.title} subtitle={`${resolved.passage_type} passage`}>
      {error ? (
        <p role="alert" className={styles.error}>
          {error}
        </p>
      ) : null}
      <Card>
        <h2>{resolved.passage_title}</h2>
        <div className={styles.chipRow}>
          <Tag>Difficulty: {difficultyLabel}</Tag>
        </div>
        <p className={styles.passage}>{resolved.passage_text}</p>
      </Card>

      <Card>
        <h2>Questions</h2>
        {resolved.questions.map((question) => (
          <article key={question.id} className={styles.question}>
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
        <Button type="button" onClick={onSubmit} disabled={isSubmitting}>
          {isSubmitting ? "Submitting..." : "Submit answers"}
        </Button>
      </Card>
    </AppShell>
  );
}

"use client";

import { useState } from "react";

import { ApiError, changePassword } from "@/lib/api";

import styles from "../app/screens.module.css";

type Status =
  | { kind: "idle" }
  | { kind: "submitting" }
  | { kind: "success"; message: string }
  | { kind: "error"; message: string };

const MIN_LENGTH = 8;

export function PasswordChangeForm() {
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [confirm, setConfirm] = useState("");
  const [status, setStatus] = useState<Status>({ kind: "idle" });

  const submitting = status.kind === "submitting";

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (next.length < MIN_LENGTH) {
      setStatus({ kind: "error", message: `New password must be at least ${MIN_LENGTH} characters.` });
      return;
    }
    if (next !== confirm) {
      setStatus({ kind: "error", message: "New password and confirmation do not match." });
      return;
    }
    if (next === current) {
      setStatus({ kind: "error", message: "New password must differ from the current password." });
      return;
    }

    setStatus({ kind: "submitting" });
    try {
      await changePassword(current, next);
      setStatus({ kind: "success", message: "Password updated. Use it next time you sign in." });
      setCurrent("");
      setNext("");
      setConfirm("");
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        setStatus({ kind: "error", message: "Current password is incorrect." });
      } else if (err instanceof ApiError && err.status === 429) {
        setStatus({ kind: "error", message: "Too many attempts. Please wait a minute and try again." });
      } else if (err instanceof ApiError && err.status === 422) {
        setStatus({ kind: "error", message: "New password did not meet the requirements." });
      } else {
        setStatus({ kind: "error", message: "Could not update password. Please try again." });
      }
    }
  };

  return (
    <form className={styles.passwordForm} onSubmit={handleSubmit} aria-label="Change password">
      <label className={styles.passwordField}>
        <span>Current password</span>
        <input
          type="password"
          autoComplete="current-password"
          value={current}
          onChange={(e) => setCurrent(e.target.value)}
          required
        />
      </label>
      <label className={styles.passwordField}>
        <span>New password</span>
        <input
          type="password"
          autoComplete="new-password"
          minLength={MIN_LENGTH}
          value={next}
          onChange={(e) => setNext(e.target.value)}
          required
        />
      </label>
      <label className={styles.passwordField}>
        <span>Confirm new password</span>
        <input
          type="password"
          autoComplete="new-password"
          minLength={MIN_LENGTH}
          value={confirm}
          onChange={(e) => setConfirm(e.target.value)}
          required
        />
      </label>
      <button type="submit" disabled={submitting} className={styles.passwordButton}>
        {submitting ? "Updating…" : "Update password"}
      </button>
      {status.kind === "success" ? (
        <p role="status" className={styles.passwordSuccess}>
          {status.message}
        </p>
      ) : null}
      {status.kind === "error" ? (
        <p role="alert" className={styles.passwordError}>
          {status.message}
        </p>
      ) : null}
    </form>
  );
}

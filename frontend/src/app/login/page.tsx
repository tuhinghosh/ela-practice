"use client";

import { FormEvent, useEffect, useState } from "react";

import { AppShell } from "@/components/app-shell";
import { Button } from "@/components/button";
import { Card } from "@/components/card";
import { Icon } from "@/components/icon";

import styles from "../screens.module.css";

export default function LoginPage() {
  const [username, setUsername] = useState("user");
  const [password, setPassword] = useState("password");
  const [error, setError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    const run = async () => {
      const response = await fetch("/api/auth/session", {
        credentials: "include",
      });
      if (!response.ok) return;

      const payload = (await response.json()) as { authenticated?: boolean };
      if (payload.authenticated) {
        window.location.href = "/";
      }
    };

    void run();
  }, []);

  const onSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError("");
    setIsSubmitting(true);

    try {
      const response = await fetch("/api/auth/login", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        credentials: "include",
        body: JSON.stringify({ username, password }),
      });

      if (!response.ok) {
        setError("Login failed. Please use user / password.");
        return;
      }

      window.location.href = "/";
    } catch {
      setError("Could not reach the server. Please try again.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <AppShell
      title="Sign in to start today's quest"
      subtitle="MVP login is currently fixed to one account for local development."
      eyebrow="Welcome"
      heroIcon="rocket"
      showNav={false}
    >
      <Card className={styles.loginCard}>
        <div className={styles.loginIntro}>
          <span className={styles.loginIconWrap} aria-hidden="true">
            <Icon name="lock" size={22} />
          </span>
          <div>
            <h2>Login</h2>
            <p className={styles.muted}>Sign in to continue your reading adventure.</p>
          </div>
        </div>
        <p className={styles.loginCredentials}>
          Use username <strong>user</strong> and password <strong>password</strong>.
        </p>
        <form onSubmit={onSubmit} className={styles.form}>
          <div>
            <label htmlFor="username" className={styles.label}>
              <Icon name="user" size={14} />
              Username
            </label>
            <input
              id="username"
              type="text"
              value={username}
              onChange={(event) => setUsername(event.target.value)}
              className={styles.input}
              autoComplete="username"
            />
          </div>
          <div>
            <label htmlFor="password" className={styles.label}>
              <Icon name="lock" size={14} />
              Password
            </label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              className={styles.input}
              autoComplete="current-password"
            />
          </div>
          {error ? (
            <p role="alert" className={styles.error}>
              <Icon name="message-circle" size={16} />
              {error}
            </p>
          ) : null}
          <Button type="submit" disabled={isSubmitting}>
            {isSubmitting ? (
              "Signing in..."
            ) : (
              <>
                Continue to mission home
                <Icon name="arrow-right" size={16} />
              </>
            )}
          </Button>
        </form>
      </Card>
    </AppShell>
  );
}

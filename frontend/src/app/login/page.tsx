"use client";

import { FormEvent, useEffect, useState } from "react";

import { AppShell } from "@/components/app-shell";
import { Button } from "@/components/button";
import { Card } from "@/components/card";

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
      showNav={false}
    >
      <Card>
        <h2>Login</h2>
        <p className={styles.muted}>
          Use username <strong>user</strong> and password <strong>password</strong>.
        </p>
        <form onSubmit={onSubmit} className={styles.form}>
          <div>
            <label htmlFor="username" className={styles.label}>
              Username
            </label>
            <input
              id="username"
              type="text"
              value={username}
              onChange={(event) => setUsername(event.target.value)}
              className={styles.input}
            />
          </div>
          <div>
            <label htmlFor="password" className={styles.label}>
              Password
            </label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              className={styles.input}
            />
          </div>
          {error ? (
            <p role="alert" className={styles.error}>
              {error}
            </p>
          ) : null}
          <Button type="submit" disabled={isSubmitting}>
            {isSubmitting ? "Signing in..." : "Continue to mission home"}
          </Button>
        </form>
      </Card>
    </AppShell>
  );
}

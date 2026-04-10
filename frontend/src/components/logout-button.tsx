"use client";

import { useState } from "react";

import styles from "./logout-button.module.css";

export function LogoutButton() {
  const [isLoading, setIsLoading] = useState(false);

  const onLogout = async () => {
    try {
      setIsLoading(true);
      await fetch("/api/auth/logout", {
        method: "POST",
        credentials: "include",
      });
    } finally {
      window.location.href = "/login";
    }
  };

  return (
    <button type="button" onClick={onLogout} className={styles.button} disabled={isLoading}>
      {isLoading ? "Logging out..." : "Logout"}
    </button>
  );
}

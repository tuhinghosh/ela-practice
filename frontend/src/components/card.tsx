import type { ReactNode } from "react";

import styles from "./ui.module.css";

type Props = {
  children: ReactNode;
  as?: "section" | "article" | "div";
  className?: string;
};

function joinClassName(className?: string) {
  return className ? `${styles.card} ${className}` : styles.card;
}

export function Card({ children, as = "section", className }: Props) {
  const combined = joinClassName(className);

  if (as === "article") {
    return <article className={combined}>{children}</article>;
  }
  if (as === "div") {
    return <div className={combined}>{children}</div>;
  }
  return <section className={combined}>{children}</section>;
}

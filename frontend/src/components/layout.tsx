import type { ReactNode } from "react";

import styles from "./layout.module.css";

type SharedProps = {
  children: ReactNode;
  className?: string;
};

function joinClassName(base: string, className?: string) {
  return className ? `${base} ${className}` : base;
}

export function Stack({ children, className }: SharedProps) {
  return <div className={joinClassName(styles.stack, className)}>{children}</div>;
}

export function Split({ children, className }: SharedProps) {
  return <section className={joinClassName(styles.split, className)}>{children}</section>;
}

export function StatGrid({ children, className }: SharedProps) {
  return <div className={joinClassName(styles.statGrid, className)}>{children}</div>;
}

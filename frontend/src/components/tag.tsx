import type { ReactNode } from "react";

import styles from "./ui.module.css";

type Props = {
  children: ReactNode;
  className?: string;
};

function joinClassName(className?: string) {
  return className ? `${styles.tag} ${className}` : styles.tag;
}

export function Tag({ children, className }: Props) {
  return <span className={joinClassName(className)}>{children}</span>;
}

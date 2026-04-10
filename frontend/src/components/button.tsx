import Link from "next/link";
import type { ButtonHTMLAttributes, ReactNode } from "react";

import styles from "./ui.module.css";

type ButtonTone = "primary" | "secondary" | "ghost";

type BaseProps = {
  children: ReactNode;
  className?: string;
  tone?: ButtonTone;
};

type ButtonProps = BaseProps & ButtonHTMLAttributes<HTMLButtonElement>;

type ButtonLinkProps = BaseProps & {
  href: string;
};

function toneClassName(tone: ButtonTone) {
  if (tone === "secondary") return styles.buttonSecondary;
  if (tone === "ghost") return styles.buttonGhost;
  return styles.buttonPrimary;
}

function joinClassName(tone: ButtonTone, className?: string) {
  const base = `${styles.button} ${toneClassName(tone)}`;
  return className ? `${base} ${className}` : base;
}

export function Button({ children, className, tone = "primary", type = "button", ...rest }: ButtonProps) {
  return (
    <button type={type} className={joinClassName(tone, className)} {...rest}>
      {children}
    </button>
  );
}

export function ButtonLink({ children, href, className, tone = "primary" }: ButtonLinkProps) {
  return (
    <Link href={href} className={joinClassName(tone, className)}>
      {children}
    </Link>
  );
}

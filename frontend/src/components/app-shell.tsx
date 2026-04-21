import Link from "next/link";
import type { ReactNode } from "react";

import { LogoutButton } from "@/components/logout-button";

import styles from "./app-shell.module.css";

type ShellProps = {
  title: string;
  subtitle?: string;
  children: ReactNode;
  showNav?: boolean;
};

const navItems = [
  { href: "/", label: "Mission Home" },
  { href: "/activity/nature-01", label: "Activity" },
  { href: "/results/session-001", label: "Results" },
  { href: "/parent/progress", label: "Parent View" },
];

export function AppShell({ title, subtitle, children, showNav = true }: ShellProps) {
  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <div className={styles.headerInner}>
          <p className={styles.brand}>Reading and Writing Adventure</p>
          {showNav ? (
            <nav className={styles.nav} aria-label="Primary">
              {navItems.map((item) => (
                <Link key={item.href} href={item.href} className={styles.navLink}>
                  {item.label}
                </Link>
              ))}
              <LogoutButton />
            </nav>
          ) : null}
        </div>
      </header>

      <main className={styles.main}>
        <section className={styles.hero}>
          <span className={styles.eyebrow}>Today&apos;s reading quest</span>
          <h1 className={styles.title}>{title}</h1>
          {subtitle ? <p className={styles.subtitle}>{subtitle}</p> : null}
        </section>
        {children}
      </main>
    </div>
  );
}

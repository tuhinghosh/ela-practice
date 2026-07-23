import Link from "next/link";
import type { ReactNode } from "react";

import { Icon, type IconName } from "@/components/icon";
import { LogoutButton } from "@/components/logout-button";

import styles from "./app-shell.module.css";

type ShellProps = {
  title: string;
  subtitle?: string;
  eyebrow?: string;
  children: ReactNode;
  showNav?: boolean;
  heroIcon?: IconName;
};

const navItems: Array<{ href: string; label: string; icon: IconName }> = [
  { href: "/", label: "Missions", icon: "home" },
  { href: "/parent/progress", label: "Parent View", icon: "users" },
];

export function AppShell({
  title,
  subtitle,
  eyebrow = "Today's reading quest",
  children,
  showNav = true,
  heroIcon = "compass",
}: ShellProps) {
  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <div className={styles.headerInner}>
          <Link href="/" className={styles.brand} aria-label="Reading and Writing Adventure home">
            <span className={styles.brandMark} aria-hidden="true">
              <Icon name="sparkles" size={20} />
            </span>
            <span className={styles.brandText}>
              <span className={styles.brandTitle}>Reading &amp; Writing</span>
              <span className={styles.brandSub}>Adventure</span>
            </span>
          </Link>
          {showNav ? (
            <nav className={styles.nav} aria-label="Primary">
              {navItems.map((item) => (
                <Link key={item.href} href={item.href} className={styles.navLink}>
                  <Icon name={item.icon} size={16} />
                  <span>{item.label}</span>
                </Link>
              ))}
              <LogoutButton />
            </nav>
          ) : null}
        </div>
      </header>

      <main className={styles.main}>
        <section className={styles.hero}>
          <div className={styles.heroContent}>
            <span className={styles.eyebrow}>
              <Icon name="sparkles" size={14} />
              {eyebrow}
            </span>
            <h1 className={styles.title}>{title}</h1>
            {subtitle ? <p className={styles.subtitle}>{subtitle}</p> : null}
          </div>
          <div className={styles.heroBadge} aria-hidden="true">
            <Icon name={heroIcon} size={36} />
          </div>
        </section>
        {children}
      </main>
    </div>
  );
}

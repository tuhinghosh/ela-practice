import type { ReactNode, SVGProps } from "react";

export type IconName =
  | "home"
  | "book"
  | "trophy"
  | "users"
  | "logout"
  | "sparkles"
  | "star"
  | "flame"
  | "target"
  | "compass"
  | "lightbulb"
  | "pencil"
  | "check-circle"
  | "arrow-right"
  | "play"
  | "filter"
  | "user"
  | "lock"
  | "trending-up"
  | "message-circle"
  | "rocket"
  | "award"
  | "clipboard-list"
  | "chevron-right"
  | "search";

type IconProps = SVGProps<SVGSVGElement> & {
  name: IconName;
  size?: number | string;
};

const PATHS: Record<IconName, ReactNode> = {
  home: (
    <>
      <path d="m3 9 9-7 9 7v11a2 2 0 0 1-2 2h-4a1 1 0 0 1-1-1v-6h-4v6a1 1 0 0 1-1 1H5a2 2 0 0 1-2-2Z" />
    </>
  ),
  book: (
    <>
      <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" />
      <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2Z" />
    </>
  ),
  trophy: (
    <>
      <path d="M8 21h8" />
      <path d="M12 17v4" />
      <path d="M7 4h10v4a5 5 0 1 1-10 0Z" />
      <path d="M17 4h3a1 1 0 0 1 1 1v2a4 4 0 0 1-4 4" />
      <path d="M7 4H4a1 1 0 0 0-1 1v2a4 4 0 0 0 4 4" />
    </>
  ),
  users: (
    <>
      <path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2" />
      <circle cx="9" cy="7" r="4" />
      <path d="M22 21v-2a4 4 0 0 0-3-3.87" />
      <path d="M16 3.13a4 4 0 0 1 0 7.75" />
    </>
  ),
  logout: (
    <>
      <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
      <path d="m16 17 5-5-5-5" />
      <path d="M21 12H9" />
    </>
  ),
  sparkles: (
    <>
      <path d="m12 3-1.5 4.5L6 9l4.5 1.5L12 15l1.5-4.5L18 9l-4.5-1.5Z" />
      <path d="M5 17 4 19l-2 1 2 1 1 2 1-2 2-1-2-1Z" />
      <path d="M19 14l-.7 2.1L16 17l2.3.9L19 20l.7-2.1L22 17l-2.3-.9Z" />
    </>
  ),
  star: (
    <>
      <path d="M12 2l3.1 6.3 6.9 1-5 4.9 1.2 6.9L12 18l-6.2 3.1L7 14.2 2 9.3l6.9-1Z" />
    </>
  ),
  flame: (
    <>
      <path d="M8.5 14.5c0-2.5 2-3.5 2-6 2 0 4 2.5 4 5.5 1.5-1 2-2.5 2-4 2 1 3.5 4 3.5 7a8 8 0 0 1-16 0c0-1.5.5-3 1.5-4 0 1.5 1.5 2.5 3 1.5Z" />
    </>
  ),
  target: (
    <>
      <circle cx="12" cy="12" r="10" />
      <circle cx="12" cy="12" r="6" />
      <circle cx="12" cy="12" r="2" />
    </>
  ),
  compass: (
    <>
      <circle cx="12" cy="12" r="10" />
      <path d="m16 8-3 9-5-3 3-9Z" />
    </>
  ),
  lightbulb: (
    <>
      <path d="M9 18h6" />
      <path d="M10 22h4" />
      <path d="M12 2a7 7 0 0 0-4 12.7c.6.6 1 1.3 1 2.2V18h6v-1.1c0-.9.4-1.6 1-2.2A7 7 0 0 0 12 2Z" />
    </>
  ),
  pencil: (
    <>
      <path d="M17 3a2.83 2.83 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5Z" />
      <path d="m15 5 4 4" />
    </>
  ),
  "check-circle": (
    <>
      <circle cx="12" cy="12" r="10" />
      <path d="m8.5 12.5 2.5 2.5 4.5-5" />
    </>
  ),
  "arrow-right": (
    <>
      <path d="M5 12h14" />
      <path d="m12 5 7 7-7 7" />
    </>
  ),
  play: (
    <>
      <path d="M6 4v16l14-8Z" />
    </>
  ),
  filter: (
    <>
      <path d="M3 4h18l-7 9v6l-4 2v-8Z" />
    </>
  ),
  user: (
    <>
      <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
      <circle cx="12" cy="7" r="4" />
    </>
  ),
  lock: (
    <>
      <rect x="3" y="11" width="18" height="11" rx="2" />
      <path d="M7 11V7a5 5 0 0 1 10 0v4" />
    </>
  ),
  "trending-up": (
    <>
      <path d="m3 17 6-6 4 4 8-8" />
      <path d="M14 7h7v7" />
    </>
  ),
  "message-circle": (
    <>
      <path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5Z" />
    </>
  ),
  rocket: (
    <>
      <path d="M4.5 16.5c-1.5 1.3-2 5-2 5s3.7-.5 5-2c.7-.9.7-2.3-.2-3.2-.9-.9-2.3-.9-3.2-.2Z" />
      <path d="M12 15c-3-3-3-7 0-12 5 0 9 4 12 0-3 5-7 5-10 8" />
      <path d="M9 12c-1 0-3.5 0-5 1.5 0 0 3 0 5 2" />
      <path d="M15 13c0 1 0 3.5-1.5 5 0 0 0-3-2-5" />
    </>
  ),
  award: (
    <>
      <circle cx="12" cy="8" r="6" />
      <path d="m15.5 13-1.4 5.6L12 17l-2.1 1.6L8.5 13" />
    </>
  ),
  "clipboard-list": (
    <>
      <rect x="8" y="2" width="8" height="4" rx="1" />
      <path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2" />
      <path d="M9 12h6" />
      <path d="M9 16h6" />
    </>
  ),
  "chevron-right": (
    <>
      <path d="m9 6 6 6-6 6" />
    </>
  ),
  search: (
    <>
      <circle cx="11" cy="11" r="7" />
      <path d="m20 20-3.5-3.5" />
    </>
  ),
};

export function Icon({ name, size = 18, ...rest }: IconProps) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.8}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      {...rest}
    >
      {PATHS[name]}
    </svg>
  );
}

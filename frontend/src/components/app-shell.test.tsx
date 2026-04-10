import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { AppShell } from "./app-shell";

describe("AppShell", () => {
  it("renders title, subtitle, and child content", () => {
    render(
      <AppShell title="Mission Home" subtitle="Quest ready">
        <p>Child content</p>
      </AppShell>,
    );

    expect(screen.getByRole("heading", { name: "Mission Home" })).toBeInTheDocument();
    expect(screen.getByText("Quest ready")).toBeInTheDocument();
    expect(screen.getByText("Child content")).toBeInTheDocument();
    expect(screen.getByRole("navigation", { name: "Primary" })).toBeInTheDocument();
  });

  it("can hide top navigation", () => {
    render(
      <AppShell title="Login" showNav={false}>
        <p>Login content</p>
      </AppShell>,
    );

    expect(screen.queryByRole("navigation", { name: "Primary" })).not.toBeInTheDocument();
  });
});

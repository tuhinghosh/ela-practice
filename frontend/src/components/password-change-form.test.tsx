import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import * as api from "@/lib/api";

import { PasswordChangeForm } from "./password-change-form";

describe("PasswordChangeForm", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  function fillFields(
    container: HTMLElement,
    values: { current: string; next: string; confirm: string },
  ): void {
    fireEvent.change(screen.getByLabelText("Current password"), {
      target: { value: values.current },
    });
    fireEvent.change(screen.getByLabelText("New password"), {
      target: { value: values.next },
    });
    fireEvent.change(screen.getByLabelText("Confirm new password"), {
      target: { value: values.confirm },
    });
  }

  it("calls changePassword and shows success", async () => {
    const spy = vi.spyOn(api, "changePassword").mockResolvedValue({ status: "ok" });

    const { container } = render(<PasswordChangeForm />);
    fillFields(container, {
      current: "password",
      next: "new-strong-password-1",
      confirm: "new-strong-password-1",
    });
    fireEvent.click(screen.getByRole("button", { name: /update password/i }));

    await waitFor(() => {
      expect(spy).toHaveBeenCalledWith("password", "new-strong-password-1");
    });
    expect(await screen.findByRole("status")).toHaveTextContent(/password updated/i);
  });

  it("validates new password length before calling the API", () => {
    const spy = vi.spyOn(api, "changePassword");
    const { container } = render(<PasswordChangeForm />);
    fillFields(container, { current: "password", next: "short", confirm: "short" });
    fireEvent.click(screen.getByRole("button", { name: /update password/i }));

    expect(spy).not.toHaveBeenCalled();
    expect(screen.getByRole("alert")).toHaveTextContent(/at least 8 characters/i);
  });

  it("rejects mismatched confirmation before calling the API", () => {
    const spy = vi.spyOn(api, "changePassword");
    const { container } = render(<PasswordChangeForm />);
    fillFields(container, {
      current: "password",
      next: "new-strong-password-1",
      confirm: "different-password-99",
    });
    fireEvent.click(screen.getByRole("button", { name: /update password/i }));

    expect(spy).not.toHaveBeenCalled();
    expect(screen.getByRole("alert")).toHaveTextContent(/do not match/i);
  });

  it("surfaces 401 from the API as a friendly error", async () => {
    vi.spyOn(api, "changePassword").mockRejectedValue(
      new api.ApiError(401, "Current password is incorrect."),
    );

    const { container } = render(<PasswordChangeForm />);
    fillFields(container, {
      current: "wrong",
      next: "new-strong-password-1",
      confirm: "new-strong-password-1",
    });
    fireEvent.click(screen.getByRole("button", { name: /update password/i }));

    expect(await screen.findByRole("alert")).toHaveTextContent(/incorrect/i);
  });

  it("surfaces 429 as a wait-and-retry message", async () => {
    vi.spyOn(api, "changePassword").mockRejectedValue(
      new api.ApiError(429, "Too many attempts."),
    );

    const { container } = render(<PasswordChangeForm />);
    fillFields(container, {
      current: "password",
      next: "new-strong-password-1",
      confirm: "new-strong-password-1",
    });
    fireEvent.click(screen.getByRole("button", { name: /update password/i }));

    expect(await screen.findByRole("alert")).toHaveTextContent(/wait a minute/i);
  });
});

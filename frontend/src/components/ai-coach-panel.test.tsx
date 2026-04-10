import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { AICoachPanel } from "./ai-coach-panel";

describe("AICoachPanel", () => {
  it("renders coach content and handles ask interaction", () => {
    const onAskCoach = vi.fn();
    const onQuestionChange = vi.fn();

    render(
      <AICoachPanel
        coach={{
          message_to_child: "Great work!",
          explanation: "You used evidence clearly.",
          celebration: "Quest complete!",
          confidence: 0.8,
          used_fallback: false,
          model: "openai/gpt-oss-120b",
          suggested_next_activity_id: "river-map",
          hint: "Use clue words.",
        }}
        question="How can I improve?"
        onQuestionChange={onQuestionChange}
        onAskCoach={onAskCoach}
        isAsking={false}
        error=""
      />,
    );

    expect(screen.getByText("Great work!")).toBeInTheDocument();
    expect(screen.getByText("Quest complete!")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Try coach suggestion" })).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("Ask the coach about this activity"), {
      target: { value: "Another question" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Ask coach" }));

    expect(onQuestionChange).toHaveBeenCalled();
    expect(onAskCoach).toHaveBeenCalled();
  });
});

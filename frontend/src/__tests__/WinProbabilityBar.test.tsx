import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { WinProbabilityBar } from "@/components/WinProbabilityBar";

describe("WinProbabilityBar", () => {
  it("sets width from percentage", () => {
    render(<WinProbabilityBar leftPct={73} />);
    const el = screen.getByTestId("prob-left");
    expect((el as HTMLElement).style.width).toBe("73%");
  });
});

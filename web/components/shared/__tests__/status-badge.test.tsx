import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { StatusBadge } from "../status-badge";

describe("StatusBadge", () => {
  it("renders score number", () => {
    render(<StatusBadge score={85} />);
    expect(screen.getByText("85")).toBeInTheDocument();
  });

  it("resolves success variant for score >= 70", () => {
    const { container } = render(<StatusBadge score={85} />);
    const badge = container.querySelector("span");
    expect(badge?.className).toContain("text-success");
  });

  it("resolves warning variant for score 40-69", () => {
    const { container } = render(<StatusBadge score={55} />);
    const badge = container.querySelector("span");
    expect(badge?.className).toContain("text-warning");
  });

  it("resolves error variant for score < 40", () => {
    const { container } = render(<StatusBadge score={25} />);
    const badge = container.querySelector("span");
    expect(badge?.className).toContain("text-destructive");
  });

  it("explicit variant overrides score", () => {
    const { container } = render(<StatusBadge score={20} variant="success" />);
    const badge = container.querySelector("span");
    expect(badge?.className).toContain("text-success");
  });

  it("renders children instead of score", () => {
    render(<StatusBadge variant="info">Custom Text</StatusBadge>);
    expect(screen.getByText("Custom Text")).toBeInTheDocument();
  });

  it("renders dot indicator in dot mode", () => {
    const { container } = render(<StatusBadge score={85} dot />);
    const dot = container.querySelector("span > span");
    expect(dot).toBeInTheDocument();
    expect(dot?.className).toContain("rounded-full");
  });

  it("resolves success variant at exact threshold (score = 70)", () => {
    const { container } = render(<StatusBadge score={70} />);
    const badge = container.querySelector("span");
    expect(badge?.className).toContain("text-success");
  });

  it("resolves warning variant at exact threshold (score = 40)", () => {
    const { container } = render(<StatusBadge score={40} />);
    const badge = container.querySelector("span");
    expect(badge?.className).toContain("text-warning");
  });

  it("resolves warning variant at boundary (score = 69)", () => {
    const { container } = render(<StatusBadge score={69} />);
    const badge = container.querySelector("span");
    expect(badge?.className).toContain("text-warning");
  });

  it("resolves error variant at boundary (score = 39)", () => {
    const { container } = render(<StatusBadge score={39} />);
    const badge = container.querySelector("span");
    expect(badge?.className).toContain("text-destructive");
  });
});

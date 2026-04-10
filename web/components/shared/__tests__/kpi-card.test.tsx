import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { KPIGrid } from "../kpi-card";
import { Eye } from "lucide-react";

describe("KPIGrid", () => {
  const cards = [
    { label: "Score", value: 85, icon: Eye },
    { label: "Count", value: 42 },
    { label: "Rate", value: "98%" },
    { label: "Total", value: 1000 },
  ];

  it("renders all card values", () => {
    render(<KPIGrid cards={cards} />);
    expect(screen.getByText("85")).toBeInTheDocument();
    expect(screen.getByText("42")).toBeInTheDocument();
    expect(screen.getByText("98%")).toBeInTheDocument();
    expect(screen.getByText("1000")).toBeInTheDocument();
  });

  it("renders all card labels", () => {
    render(<KPIGrid cards={cards} />);
    expect(screen.getByText("Score")).toBeInTheDocument();
    expect(screen.getByText("Count")).toBeInTheDocument();
    expect(screen.getByText("Rate")).toBeInTheDocument();
    expect(screen.getByText("Total")).toBeInTheDocument();
  });

  it("renders trend indicators", () => {
    const trendCards = [
      { label: "Score", value: 85, trend: { value: 12, direction: "up" as const } },
    ];
    render(<KPIGrid cards={trendCards} />);
    expect(screen.getByText("12%")).toBeInTheDocument();
  });
});

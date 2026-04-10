import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { PageHeader } from "../page-header";
import { Button } from "@/components/ui/button";

describe("PageHeader", () => {
  it("renders title", () => {
    render(<PageHeader title="Dashboard" />);
    expect(screen.getByText("Dashboard")).toBeInTheDocument();
  });

  it("renders description when provided", () => {
    render(<PageHeader title="Dashboard" description="Overview" />);
    expect(screen.getByText("Overview")).toBeInTheDocument();
  });

  it("renders actions slot", () => {
    render(<PageHeader title="Test" actions={<Button>Click me</Button>} />);
    expect(screen.getByText("Click me")).toBeInTheDocument();
  });

  it("renders tabs slot", () => {
    render(<PageHeader title="Test" tabs={<div data-testid="tabs">Tabs</div>} />);
    expect(screen.getByTestId("tabs")).toBeInTheDocument();
  });
});

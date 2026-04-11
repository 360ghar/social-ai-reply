import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { EmptyState } from "../empty-state";
import { AlertCircle } from "lucide-react";

describe("EmptyState", () => {
  it("renders title", () => {
    render(<EmptyState title="No data" />);
    expect(screen.getByText("No data")).toBeInTheDocument();
  });

  it("renders description when provided", () => {
    render(<EmptyState title="No data" description="Try again later" />);
    expect(screen.getByText("Try again later")).toBeInTheDocument();
  });

  it("renders icon when provided", () => {
    const { container } = render(<EmptyState title="No data" icon={AlertCircle} />);
    expect(container.querySelector("svg")).toBeInTheDocument();
  });

  it("renders action button and fires onClick", () => {
    const onClick = vi.fn();
    render(<EmptyState title="No data" action={{ label: "Retry", onClick }} />);
    const button = screen.getByText("Retry");
    expect(button).toBeInTheDocument();
    fireEvent.click(button);
    expect(onClick).toHaveBeenCalledOnce();
  });

  it("works without optional props", () => {
    render(<EmptyState title="Empty" />);
    expect(screen.getByText("Empty")).toBeInTheDocument();
  });
});

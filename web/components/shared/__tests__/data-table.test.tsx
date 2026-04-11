import { describe, it, expect, vi } from "vitest";
import { render, screen, within } from "@testing-library/react";
import { DataTable } from "../data-table";

describe("DataTable", () => {
  const columns = [
    { key: "name", header: "Name" },
    { key: "role", header: "Role" },
  ];
  const data = [
    { id: "1", name: "Alice", role: "Admin" },
    { id: "2", name: "Bob", role: "User" },
  ];

  it("renders column headers", () => {
    render(<DataTable columns={columns} data={data as any} />);
    // Get the desktop table header specifically
    const table = screen.getByRole("table");
    expect(within(table).getByText("Name")).toBeInTheDocument();
    expect(within(table).getByText("Role")).toBeInTheDocument();
  });

  it("renders cell values", () => {
    render(<DataTable columns={columns} data={data as any} />);
    // Use getAllByText since values appear in both desktop and mobile views
    expect(screen.getAllByText("Alice")).toHaveLength(2);
    expect(screen.getAllByText("Bob")).toHaveLength(2);
  });

  it("renders custom column render function", () => {
    const cols = [
      { key: "name", header: "Name", render: (row: any) => <strong>{row.name}</strong> },
    ];
    render(<DataTable columns={cols} data={data as any} />);
    // Get all strong elements with "Alice" and verify at least one exists
    const strongElements = screen.getAllByText("Alice");
    expect(strongElements.length).toBeGreaterThanOrEqual(1);
    expect(strongElements[0].tagName).toBe("STRONG");
  });

  it("shows custom empty state when data is empty", () => {
    render(<DataTable columns={columns} data={[]} emptyState={{ title: "No items" }} />);
    expect(screen.getByText("No items")).toBeInTheDocument();
  });

  it("shows default empty state when no emptyState prop and data is empty", () => {
    render(<DataTable columns={columns} data={[]} />);
    expect(screen.getByText("No data")).toBeInTheDocument();
  });

  it("forwards action prop in emptyState", () => {
    const onClick = vi.fn();
    render(<DataTable columns={columns} data={[]} emptyState={{ title: "Empty", action: { label: "Add", onClick } }} />);
    const button = screen.getByText("Add");
    expect(button).toBeInTheDocument();
    button.click();
    expect(onClick).toHaveBeenCalledTimes(1);
  });
});

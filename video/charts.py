#!/usr/bin/env python3
"""
Chart generation for the wiki video overview.

Uses matplotlib to generate branded charts that are embedded into video slides.
"""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


# Brand colors
BRAND_BLUE = "#3B82F6"
BRAND_DARK = "#0F172A"
BRAND_GRAY = "#94A3B8"
BRAND_WHITE = "#FFFFFF"
BRAND_ACCENT = "#60A5FA"


def _apply_branding(axes: plt.Axes, title: str) -> None:
    """Apply 360 Flatmates brand styling to a chart."""
    axes.set_facecolor(BRAND_DARK)
    axes.tick_params(colors=BRAND_GRAY)
    axes.title.set_color(BRAND_WHITE)
    axes.title.set_fontsize(16)
    axes.title.set_fontweight("bold")
    axes.spines["top"].set_color(BRAND_GRAY)
    axes.spines["bottom"].set_color(BRAND_GRAY)
    axes.spines["left"].set_color(BRAND_GRAY)
    axes.spines["right"].set_color(BRAND_GRAY)
    axes.set_title(title)


def create_relevance_chart(output_path: Path) -> Path:
    """Create a horizontal bar chart of the relevance scoring breakdown."""
    fig, axes = plt.subplots(figsize=(8, 4.5), dpi=150)
    fig.patch.set_facecolor(BRAND_DARK)

    factors = ["Semantic", "Keywords", "Intent", "Source Fit", "Pain Points", "Freshness"]
    weights = [30, 25, 20, 10, 10, 5]
    colors = [BRAND_ACCENT, BRAND_BLUE, BRAND_BLUE, BRAND_GRAY, BRAND_GRAY, BRAND_GRAY]

    y_positions = np.arange(len(factors))
    axes.barh(y_positions, weights, color=colors, height=0.6)
    axes.set_yticks(y_positions)
    axes.set_yticklabels(factors)
    axes.set_xlim(0, 40)
    axes.set_xlabel("Weight %", color=BRAND_GRAY, fontsize=12)
    axes.invert_yaxis()

    for i, v in enumerate(weights):
        axes.text(v + 1, i, f"{v}%", color=BRAND_WHITE, va="center", fontsize=11)

    _apply_branding(axes, "Relevance Scoring Weights")
    fig.tight_layout()
    fig.savefig(output_path, facecolor=BRAND_DARK, edgecolor="none")
    plt.close(fig)
    return output_path


def create_agent_coverage_chart(output_path: Path) -> Path:
    """Create a grouped bar chart showing agent coverage by channel type."""
    fig, axes = plt.subplots(figsize=(8, 4.5), dpi=150)
    fig.patch.set_facecolor(BRAND_DARK)

    categories = ["Discovery", "Analysis", "Content"]
    counts = [2, 4, 4]
    colors = [BRAND_BLUE, BRAND_ACCENT, BRAND_GRAY]

    x_positions = np.arange(len(categories))
    axes.bar(x_positions, counts, color=colors, width=0.5)
    axes.set_xticks(x_positions)
    axes.set_xticklabels(categories)
    axes.set_ylim(0, 6)
    axes.set_ylabel("Number of Agents", color=BRAND_GRAY, fontsize=12)

    for i, v in enumerate(counts):
        axes.text(i, v + 0.2, str(v), color=BRAND_WHITE, ha="center", fontsize=12, fontweight="bold")

    _apply_branding(axes, "Agents by Category")
    fig.tight_layout()
    fig.savefig(output_path, facecolor=BRAND_DARK, edgecolor="none")
    plt.close(fig)
    return output_path


def create_tech_stack_chart(output_path: Path) -> Path:
    """Create a bubble chart representing the tech stack layers."""
    fig, axes = plt.subplots(figsize=(8, 4.5), dpi=150)
    fig.patch.set_facecolor(BRAND_DARK)

    layers = ["Frontend", "Backend", "Database", "LLM", "Agents"]
    sizes = [1200, 1500, 1000, 1100, 1800]
    x = [1, 2, 3, 4, 2.5]
    y = [3, 3, 1, 2, 4]
    colors = [BRAND_ACCENT, BRAND_BLUE, BRAND_GRAY, BRAND_ACCENT, BRAND_BLUE]

    scatter = axes.scatter(x, y, s=sizes, c=colors, alpha=0.7, edgecolors=BRAND_WHITE, linewidths=1.5)

    for i, label in enumerate(layers):
        axes.text(x[i], y[i], label, color=BRAND_WHITE, ha="center", va="center", fontsize=10, fontweight="bold")

    axes.set_xlim(0, 5)
    axes.set_ylim(0, 5)
    axes.axis("off")

    _apply_branding(axes, "Tech Stack Layers")
    fig.tight_layout()
    fig.savefig(output_path, facecolor=BRAND_DARK, edgecolor="none")
    plt.close(fig)
    return output_path


def create_deployment_flowchart(output_path: Path) -> Path:
    """Create a simple flowchart-style diagram for deployment."""
    fig, axes = plt.subplots(figsize=(8, 4.5), dpi=150)
    fig.patch.set_facecolor(BRAND_DARK)
    axes.set_facecolor(BRAND_DARK)

    steps = ["GitHub Push", "Railway Build", "Netlify Build", "Supabase DB", "Live Site"]
    x_positions = np.linspace(0.5, 4.5, len(steps))
    y_position = 0.5

    for i, (x, step) in enumerate(zip(x_positions, steps)):
        color = BRAND_BLUE if i < len(steps) - 1 else BRAND_ACCENT
        axes.scatter(x, y_position, s=2000, c=color, zorder=3, edgecolors=BRAND_WHITE, linewidths=2)
        axes.text(x, y_position, str(i + 1), color=BRAND_WHITE, ha="center", va="center", fontsize=12, fontweight="bold")
        axes.text(x, y_position - 0.25, step, color=BRAND_GRAY, ha="center", va="top", fontsize=9)

    # Draw connecting arrows
    for i in range(len(x_positions) - 1):
        axes.annotate(
            "",
            xy=(x_positions[i + 1] - 0.15, y_position),
            xytext=(x_positions[i] + 0.15, y_position),
            arrowprops=dict(arrowstyle="->", color=BRAND_ACCENT, lw=2),
        )

    axes.set_xlim(0, 5)
    axes.set_ylim(0, 1)
    axes.axis("off")
    axes.set_title("Deployment Pipeline", color=BRAND_WHITE, fontsize=16, fontweight="bold", pad=20)

    fig.tight_layout()
    fig.savefig(output_path, facecolor=BRAND_DARK, edgecolor="none")
    plt.close(fig)
    return output_path


def generate_all_charts(output_dir: Path) -> dict[str, Path]:
    """Generate all chart images and return their paths."""
    output_dir.mkdir(parents=True, exist_ok=True)
    charts = {
        "relevance": create_relevance_chart(output_dir / "relevance_chart.png"),
        "agents": create_agent_coverage_chart(output_dir / "agent_coverage_chart.png"),
        "tech_stack": create_tech_stack_chart(output_dir / "tech_stack_chart.png"),
        "deployment": create_deployment_flowchart(output_dir / "deployment_flowchart.png"),
    }
    return charts


if __name__ == "__main__":
    paths = generate_all_charts(Path("video/charts"))
    for name, path in paths.items():
        print(f"Generated {name}: {path}")

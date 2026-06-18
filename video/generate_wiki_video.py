#!/usr/bin/env python3
"""
Wiki Video Generator for Social AI Reply / RedditFlow

This script generates a video overview of the wiki documentation.
It can be run independently and the code is kept for future editing.

Usage:
    python video/generate_wiki_video.py

Output:
    video/overview.mp4 - Video overview of the wiki
"""

import os
import sys
from pathlib import Path

import numpy as np
from moviepy import (
    AudioFileClip,
    ColorClip,
    CompositeVideoClip,
    ImageClip,
    TextClip,
    concatenate_videoclips,
)
from PIL import Image, ImageDraw, ImageFont


class WikiVideoGenerator:
    """Generates a video overview of the wiki documentation."""

    def __init__(self, wiki_dir: str = "wiki", output_dir: str = "video"):
        self.wiki_dir = Path(wiki_dir)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)

        # Video settings
        self.width = 1920
        self.height = 1080
        self.fps = 30
        self.slide_duration = 4  # seconds per slide
        self.transition_duration = 0.5  # seconds for transitions

        # Colors
        self.bg_color = (15, 23, 42)  # Dark blue-gray
        self.text_color = (255, 255, 255)  # White
        self.accent_color = (59, 130, 246)  # Blue
        self.secondary_color = (148, 163, 184)  # Gray

    def create_title_slide(self) -> ImageClip:
        """Create the title slide."""
        # Create a blank image
        img = Image.new("RGB", (self.width, self.height), self.bg_color)
        draw = ImageDraw.Draw(img)

        # Try to load a font, fallback to default
        try:
            title_font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 72)
            subtitle_font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 36)
        except (OSError, IOError):
            title_font = ImageFont.load_default()
            subtitle_font = ImageFont.load_default()

        # Draw title
        title = "Social AI Reply / RedditFlow"
        subtitle = "Wiki Documentation Overview"
        branding = "360 Flatmates"

        # Center text
        title_bbox = draw.textbbox((0, 0), title, font=title_font)
        title_width = title_bbox[2] - title_bbox[0]
        title_x = (self.width - title_width) // 2
        title_y = self.height // 2 - 100

        draw.text((title_x, title_y), title, fill=self.text_color, font=title_font)

        # Subtitle
        subtitle_bbox = draw.textbbox((0, 0), subtitle, font=subtitle_font)
        subtitle_width = subtitle_bbox[2] - subtitle_bbox[0]
        subtitle_x = (self.width - subtitle_width) // 2
        subtitle_y = title_y + 100

        draw.text(
            (subtitle_x, subtitle_y), subtitle, fill=self.secondary_color, font=subtitle_font
        )

        # Branding
        branding_bbox = draw.textbbox((0, 0), branding, font=subtitle_font)
        branding_width = branding_bbox[2] - branding_bbox[0]
        branding_x = (self.width - branding_width) // 2
        branding_y = self.height - 100

        draw.text(
            (branding_x, branding_y), branding, fill=self.accent_color, font=subtitle_font
        )

        # Convert to moviepy clip
        img_array = np.array(img)
        return ImageClip(img_array).with_duration(self.slide_duration)

    def create_section_slide(self, title: str, items: list[str]) -> ImageClip:
        """Create a section slide with title and bullet points."""
        img = Image.new("RGB", (self.width, self.height), self.bg_color)
        draw = ImageDraw.Draw(img)

        try:
            title_font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 48)
            item_font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 28)
        except (OSError, IOError):
            title_font = ImageFont.load_default()
            item_font = ImageFont.load_default()

        # Draw title
        draw.text((100, 100), title, fill=self.accent_color, font=title_font)

        # Draw items
        y_offset = 200
        for item in items[:8]:  # Limit to 8 items
            draw.text((150, y_offset), f"• {item}", fill=self.text_color, font=item_font)
            y_offset += 50

        img_array = np.array(img)
        return ImageClip(img_array).with_duration(self.slide_duration)

    def create_architecture_slide(self) -> ImageClip:
        """Create an architecture overview slide."""
        img = Image.new("RGB", (self.width, self.height), self.bg_color)
        draw = ImageDraw.Draw(img)

        try:
            title_font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 48)
            box_font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 24)
        except (OSError, IOError):
            title_font = ImageFont.load_default()
            box_font = ImageFont.load_default()

        # Title
        draw.text((100, 50), "Architecture Overview", fill=self.accent_color, font=title_font)

        # Draw architecture boxes
        boxes = [
            {"title": "Frontend", "items": ["Next.js 16", "React 19", "Tailwind CSS"], "x": 100, "y": 200},
            {"title": "Backend", "items": ["FastAPI", "Python 3.11", "Supabase"], "x": 700, "y": 200},
            {"title": "Agents", "items": ["10 Specialized", "Multi-agent", "System"], "x": 1300, "y": 200},
            {"title": "Database", "items": ["Supabase Postgres", "Redis Cache", "File Storage"], "x": 100, "y": 600},
            {"title": "LLM", "items": ["Gemini", "OpenAI", "Claude"], "x": 700, "y": 600},
            {"title": "External", "items": ["Reddit API", "HN API", "Web Scraping"], "x": 1300, "y": 600},
        ]

        for box in boxes:
            # Draw box background
            draw.rectangle(
                [box["x"], box["y"], box["x"] + 400, box["y"] + 200],
                fill=(30, 41, 59),
                outline=self.accent_color,
                width=2,
            )

            # Draw box title
            draw.text(
                (box["x"] + 20, box["y"] + 20),
                box["title"],
                fill=self.text_color,
                font=box_font,
            )

            # Draw box items
            y_offset = box["y"] + 60
            for item in box["items"]:
                draw.text(
                    (box["x"] + 40, y_offset),
                    f"• {item}",
                    fill=self.secondary_color,
                    font=box_font,
                )
                y_offset += 30

        img_array = np.array(img)
        return ImageClip(img_array).with_duration(self.slide_duration * 2)  # Longer for complex slide

    def create_agents_slide(self) -> ImageClip:
        """Create a slide showing all 10 agents."""
        img = Image.new("RGB", (self.width, self.height), self.bg_color)
        draw = ImageDraw.Draw(img)

        try:
            title_font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 48)
            agent_font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 24)
        except (OSError, IOError):
            title_font = ImageFont.load_default()
            agent_font = ImageFont.load_default()

        # Title
        draw.text((100, 50), "10 Specialized Agents", fill=self.accent_color, font=title_font)

        # Agent list
        agents = [
            "Brand Brain - Website analysis",
            "Reddit Agent - Post discovery",
            "Hacker News Agent - Tech discussions",
            "SEO Agent - Website audit",
            "GEO Agent - AI search visibility",
            "Articles Agent - Content briefs",
            "X Agent - Twitter ideas",
            "LinkedIn Agent - Professional posts",
            "UGC Agent - Video briefs",
            "Technical SEO Agent - Code audit",
        ]

        # Draw agents in two columns
        y_offset = 150
        for i, agent in enumerate(agents):
            x_offset = 100 if i < 5 else 900
            if i == 5:
                y_offset = 150

            draw.text((x_offset, y_offset), f"{i+1}. {agent}", fill=self.text_color, font=agent_font)
            y_offset += 60

        img_array = np.array(img)
        return ImageClip(img_array).with_duration(self.slide_duration * 2)

    def generate_video(self) -> str:
        """Generate the complete video."""
        print("Generating wiki video overview...")

        # Create slides
        slides = [
            self.create_title_slide(),
            self.create_section_slide(
                "Core Features",
                [
                    "Multi-agent AI marketing platform",
                    "Transparent relevance scoring",
                    "Manual posting (no auto-posting)",
                    "Free/open-source-first approach",
                    "10 specialized marketing agents",
                    "LLM provider flexibility",
                ],
            ),
            self.create_architecture_slide(),
            self.create_agents_slide(),
            self.create_section_slide(
                "Technical Stack",
                [
                    "Backend: FastAPI + Python 3.11",
                    "Frontend: Next.js 16 + React 19",
                    "Database: Supabase Postgres",
                    "Auth: Supabase Auth with JWT",
                    "Embeddings: TF-IDF + sentence-transformers",
                    "LLM: Gemini, OpenAI, Claude, Perplexity",
                ],
            ),
            self.create_section_slide(
                "Deployment",
                [
                    "Backend: Railway",
                    "Frontend: Netlify",
                    "Database: Supabase (managed)",
                    "CI/CD: GitHub Actions",
                    "Automatic wiki publishing",
                ],
            ),
        ]

        # Concatenate slides
        final_video = concatenate_videoclips(slides, method="compose")

        # Write output
        output_path = self.output_dir / "overview.mp4"
        final_video.write_videofile(
            str(output_path),
            fps=self.fps,
            codec="libx264",
            audio=False,
            logger=None,
        )

        print(f"Video generated: {output_path}")
        return str(output_path)


def main():
    """Main entry point."""
    generator = WikiVideoGenerator()
    output_path = generator.generate_video()
    print(f"Video saved to: {output_path}")


if __name__ == "__main__":
    main()

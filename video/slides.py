"""
Shared slide generation for wiki video overview.

This module contains the common slide rendering logic used by both
the moviepy and PIL/ffmpeg video generators. Each generator only
implements its video-encoding backend.

Usage:
    from video.slides import SlideRenderer

    renderer = SlideRenderer()
    title_slide = renderer.create_title_slide()  # Returns PIL Image
    section_slide = renderer.create_section_slide("Title", ["Item 1", "Item 2"])
"""

from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from video.charts import generate_all_charts


# Brand colors
BRAND_DARK = (15, 23, 42)
BRAND_DARKER = (30, 41, 59)
BRAND_BLUE = (59, 130, 246)
BRAND_LIGHT_BLUE = (96, 165, 250)
BRAND_WHITE = (255, 255, 255)
BRAND_GRAY = (148, 163, 184)


class SlideRenderer:
    """Renders branded slide images for the wiki video overview."""

    def __init__(self, width: int = 1920, height: int = 1080):
        self.width = width
        self.height = height

        # Cache chart images
        self.chart_dir = Path("video/charts")
        self.chart_paths = generate_all_charts(self.chart_dir)

    def _load_font(self, size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
        """Load a font with fallback to default."""
        try:
            return ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", size)
        except (OSError, IOError):
            return ImageFont.load_default()

    def _create_gradient_background(self, img: Image.Image) -> None:
        """Draw a subtle diagonal gradient background."""
        pixels = img.load()
        for y in range(self.height):
            for x in range(self.width):
                # Diagonal gradient from dark blue-gray to slightly lighter
                ratio = (x / self.width + y / self.height) / 2
                r = int(BRAND_DARK[0] + ratio * 8)
                g = int(BRAND_DARK[1] + ratio * 12)
                b = int(BRAND_DARK[2] + ratio * 16)
                pixels[x, y] = (r, g, b)

    def _draw_brand_shape(self, draw: ImageDraw.Draw) -> None:
        """Draw a 360 Flatmates brand shape in the top-right corner."""
        # Draw a stylized circle-square combined shape
        center_x = self.width - 120
        center_y = 120
        radius = 60

        # Outer circle
        draw.ellipse(
            [center_x - radius, center_y - radius, center_x + radius, center_y + radius],
            outline=BRAND_BLUE,
            width=4,
        )
        # Inner rotated square
        square_size = 35
        draw.rectangle(
            [
                center_x - square_size,
                center_y - square_size,
                center_x + square_size,
                center_y + square_size,
            ],
            outline=BRAND_LIGHT_BLUE,
            width=3,
        )

    def _draw_footer(self, draw: ImageDraw.Draw, slide_number: int, total_slides: int) -> None:
        """Draw a branded footer with progress bar and slide number."""
        footer_height = 40
        footer_y = self.height - footer_height

        # Footer background
        draw.rectangle(
            [0, footer_y, self.width, self.height],
            fill=BRAND_DARKER,
        )

        # Progress bar
        progress = (slide_number + 1) / total_slides
        progress_width = int(self.width * progress)
        draw.rectangle(
            [0, footer_y, progress_width, footer_y + 4],
            fill=BRAND_BLUE,
        )

        # Slide number
        footer_font = self._load_font(18)
        label = f"360 Flatmates  |  {slide_number + 1} / {total_slides}"
        draw.text((30, footer_y + 12), label, fill=BRAND_GRAY, font=footer_font)

    def _create_base_slide(self, slide_number: int, total_slides: int) -> tuple[Image.Image, ImageDraw.Draw]:
        """Create a base slide with gradient, brand shape, and footer."""
        img = Image.new("RGB", (self.width, self.height))
        self._create_gradient_background(img)
        draw = ImageDraw.Draw(img)
        self._draw_brand_shape(draw)
        self._draw_footer(draw, slide_number, total_slides)
        return img, draw

    def create_title_slide(self) -> Image.Image:
        """Create the title slide."""
        img, draw = self._create_base_slide(0, 9)

        title_font = self._load_font(80)
        subtitle_font = self._load_font(40)
        tagline_font = self._load_font(28)

        title = "Social AI Reply"
        subtitle = "Wiki Documentation Overview"
        tagline = "Multi-Agent AI Marketing Platform by 360 Flatmates"

        # Draw main title
        title_bbox = draw.textbbox((0, 0), title, font=title_font)
        title_width = title_bbox[2] - title_bbox[0]
        draw.text(
            ((self.width - title_width) // 2, self.height // 2 - 140),
            title,
            fill=BRAND_WHITE,
            font=title_font,
        )

        # Draw subtitle
        subtitle_bbox = draw.textbbox((0, 0), subtitle, font=subtitle_font)
        subtitle_width = subtitle_bbox[2] - subtitle_bbox[0]
        draw.text(
            ((self.width - subtitle_width) // 2, self.height // 2 - 20),
            subtitle,
            fill=BRAND_LIGHT_BLUE,
            font=subtitle_font,
        )

        # Draw tagline
        tagline_bbox = draw.textbbox((0, 0), tagline, font=tagline_font)
        tagline_width = tagline_bbox[2] - tagline_bbox[0]
        draw.text(
            ((self.width - tagline_width) // 2, self.height // 2 + 60),
            tagline,
            fill=BRAND_GRAY,
            font=tagline_font,
        )

        return img

    def create_brand_intro_slide(self) -> Image.Image:
        """Create a 360 Flatmates brand intro slide."""
        img, draw = self._create_base_slide(1, 9)

        title_font = self._load_font(56)
        body_font = self._load_font(32)

        draw.text((120, 120), "Built by 360 Flatmates", fill=BRAND_BLUE, font=title_font)

        messages = [
            "Find relevant social opportunities",
            "Generate safe, helpful drafts",
            "Grow your brand without spam",
            "Free / open-source-first platform",
        ]

        y_offset = 260
        for message in messages:
            draw.text((170, y_offset), f"\u2713 {message}", fill=BRAND_WHITE, font=body_font)
            y_offset += 70

        return img

    def create_section_slide(self, title: str, items: list[str], slide_number: int, total_slides: int) -> Image.Image:
        """Create a section slide with title and bullet points."""
        img, draw = self._create_base_slide(slide_number, total_slides)

        title_font = self._load_font(48)
        item_font = self._load_font(30)

        draw.text((120, 120), title, fill=BRAND_BLUE, font=title_font)

        y_offset = 240
        for item in items[:8]:
            draw.text((170, y_offset), f"\u2022 {item}", fill=BRAND_WHITE, font=item_font)
            y_offset += 60

        return img

    def create_chart_slide(self, chart_name: str, title: str, slide_number: int, total_slides: int) -> Image.Image:
        """Create a slide with a chart image embedded."""
        img, draw = self._create_base_slide(slide_number, total_slides)

        title_font = self._load_font(48)
        draw.text((120, 80), title, fill=BRAND_BLUE, font=title_font)

        chart_path = self.chart_paths.get(chart_name)
        if chart_path and chart_path.exists():
            chart_img = Image.open(chart_path).convert("RGB")
            # Scale chart to fit nicely
            target_width = 1400
            ratio = target_width / chart_img.width
            target_height = int(chart_img.height * ratio)
            chart_img = chart_img.resize((target_width, target_height), Image.Resampling.LANCZOS)

            x = (self.width - target_width) // 2
            y = (self.height - target_height) // 2 + 20
            img.paste(chart_img, (x, y))

        return img

    def create_architecture_slide(self, slide_number: int, total_slides: int) -> Image.Image:
        """Create an architecture overview slide."""
        img, draw = self._create_base_slide(slide_number, total_slides)

        title_font = self._load_font(48)
        box_font = self._load_font(22)

        draw.text((120, 80), "Architecture Overview", fill=BRAND_BLUE, font=title_font)

        boxes = [
            {"title": "Frontend", "items": ["Next.js 16", "React 19", "Tailwind CSS"], "x": 100, "y": 200},
            {"title": "Backend", "items": ["FastAPI", "Python 3.11", "Supabase"], "x": 700, "y": 200},
            {"title": "Agents", "items": ["10 Specialized", "Multi-agent", "System"], "x": 1300, "y": 200},
            {"title": "Database", "items": ["Supabase Postgres", "Redis Cache", "File Storage"], "x": 100, "y": 560},
            {"title": "LLM", "items": ["Gemini", "OpenAI", "Claude"], "x": 700, "y": 560},
            {"title": "External", "items": ["Reddit API", "HN API", "Web Scraping"], "x": 1300, "y": 560},
        ]

        for box in boxes:
            draw.rectangle(
                [box["x"], box["y"], box["x"] + 450, box["y"] + 210],
                fill=BRAND_DARKER,
                outline=BRAND_BLUE,
                width=2,
            )
            draw.text((box["x"] + 20, box["y"] + 20), box["title"], fill=BRAND_WHITE, font=box_font)

            y_offset = box["y"] + 60
            for item in box["items"]:
                draw.text((box["x"] + 40, y_offset), f"\u2022 {item}", fill=BRAND_GRAY, font=box_font)
                y_offset += 32

        return img

    def create_agents_slide(self, slide_number: int, total_slides: int) -> Image.Image:
        """Create a slide showing all 10 agents."""
        img, draw = self._create_base_slide(slide_number, total_slides)

        title_font = self._load_font(48)
        agent_font = self._load_font(24)

        draw.text((120, 80), "10 Specialized Agents", fill=BRAND_BLUE, font=title_font)

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

        y_offset = 180
        for i, agent in enumerate(agents):
            x_offset = 120 if i < 5 else 980
            if i == 5:
                y_offset = 180

            # Draw small brand bullet
            draw.ellipse([x_offset - 5, y_offset + 8, x_offset + 15, y_offset + 28], fill=BRAND_BLUE)
            draw.text((x_offset + 30, y_offset), agent, fill=BRAND_WHITE, font=agent_font)
            y_offset += 62

        return img

    def create_roadmap_slide(self, slide_number: int, total_slides: int) -> Image.Image:
        """Create a roadmap/timeline slide."""
        img, draw = self._create_base_slide(slide_number, total_slides)

        title_font = self._load_font(48)
        item_font = self._load_font(26)

        draw.text((120, 80), "Platform Roadmap", fill=BRAND_BLUE, font=title_font)

        milestones = [
            ("Now", "10 agents, relevance engine, manual posting"),
            ("Next", "More platform integrations, analytics v2"),
            ("Future", "Automated scheduling, advanced AI insights"),
        ]

        y_offset = 220
        for phase, description in milestones:
            draw.rectangle([120, y_offset, 280, y_offset + 50], fill=BRAND_BLUE)
            phase_bbox = draw.textbbox((0, 0), phase, font=item_font)
            phase_width = phase_bbox[2] - phase_bbox[0]
            draw.text(
                (200 - phase_width // 2, y_offset + 10),
                phase,
                fill=BRAND_WHITE,
                font=item_font,
            )
            draw.text((320, y_offset + 10), description, fill=BRAND_WHITE, font=item_font)
            y_offset += 90

        return img

    def create_outro_slide(self) -> Image.Image:
        """Create the final call-to-action slide."""
        img, draw = self._create_base_slide(8, 9)

        title_font = self._load_font(64)
        subtitle_font = self._load_font(32)

        title = "Start Growing with 360 Flatmates"
        subtitle = "Explore the wiki to learn more about Social AI Reply"

        title_bbox = draw.textbbox((0, 0), title, font=title_font)
        title_width = title_bbox[2] - title_bbox[0]
        draw.text(
            ((self.width - title_width) // 2, self.height // 2 - 80),
            title,
            fill=BRAND_WHITE,
            font=title_font,
        )

        subtitle_bbox = draw.textbbox((0, 0), subtitle, font=subtitle_font)
        subtitle_width = subtitle_bbox[2] - subtitle_bbox[0]
        draw.text(
            ((self.width - subtitle_width) // 2, self.height // 2 + 40),
            subtitle,
            fill=BRAND_GRAY,
            font=subtitle_font,
        )

        return img

    def get_all_slides(self) -> list[tuple[Image.Image, float]]:
        """Return all slides with their durations (seconds).

        Returns:
            List of (image, duration_seconds) tuples.
        """
        total_slides = 9
        return [
            (self.create_title_slide(), 5.0),
            (self.create_brand_intro_slide(), 5.0),
            (self.create_section_slide(
                "Core Features",
                [
                    "Multi-agent AI marketing platform",
                    "Transparent relevance scoring",
                    "Manual posting (no auto-posting)",
                    "Free/open-source-first approach",
                    "10 specialized marketing agents",
                    "LLM provider flexibility",
                ],
                2,
                total_slides,
            ), 5.0),
            (self.create_chart_slide("relevance", "Relevance Scoring", 3, total_slides), 6.0),
            (self.create_architecture_slide(4, total_slides), 7.0),
            (self.create_agents_slide(5, total_slides), 7.0),
            (self.create_chart_slide("agents", "Agent Coverage", 6, total_slides), 6.0),
            (self.create_chart_slide("deployment", "Deployment Pipeline", 7, total_slides), 6.0),
            (self.create_outro_slide(), 5.0),
        ]

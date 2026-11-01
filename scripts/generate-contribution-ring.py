#!/usr/bin/env python3
"""Generate a looping seven-ring contribution GIF from data/github.json."""

import json
import math
from datetime import datetime
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
DATA_FILE = ROOT / "data" / "github.json"
OUTPUT_FILE = ROOT / "assets" / "contribution-rings.gif"

WIDTH = HEIGHT = 900
SCALE = 2
CANVAS = (WIDTH * SCALE, HEIGHT * SCALE)
CENTER = (CANVAS[0] // 2, CANVAS[1] // 2 - 12)
EMPTY = "#ebedf0"
LEVEL_COLORS = ["#ebedf0", "#ffb380", "#ff944d", "#ff7518", "#d95d00"]
TEXT = "#24292f"
MUTED = "#667085"
BACKGROUND = "#ffffff"


def font(size, bold=False):
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
    ]
    for candidate in candidates:
        try:
            return ImageFont.truetype(candidate, size * SCALE)
        except OSError:
            pass
    return ImageFont.load_default()


def polar(radius, angle):
    radians = math.radians(angle)
    return (
        CENTER[0] + math.cos(radians) * radius * SCALE,
        CENTER[1] + math.sin(radians) * radius * SCALE,
    )


def ring_segment(draw, inner_radius, outer_radius, start_angle, end_angle, color):
    # A polygon gives each week a clean, slightly separated radial segment.
    points = []
    steps = max(3, int((end_angle - start_angle) / 2))
    for i in range(steps + 1):
        angle = start_angle + (end_angle - start_angle) * i / steps
        points.append(polar(outer_radius, angle))
    for i in range(steps, -1, -1):
        angle = start_angle + (end_angle - start_angle) * i / steps
        points.append(polar(inner_radius, angle))
    draw.polygon(points, fill=color)


def centered_text(draw, y, value, chosen_font, fill):
    box = draw.textbbox((0, 0), value, font=chosen_font)
    x = (CANVAS[0] - (box[2] - box[0])) // 2
    draw.text((x, y * SCALE), value, font=chosen_font, fill=fill)


def main():
    if not DATA_FILE.exists():
        raise FileNotFoundError("data/github.json is missing. Run scripts/fetch-github.mjs first.")

    data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    days = data["days"]
    if not days:
        raise ValueError("The contribution calendar contains no days.")

    # Group the API's chronological days into weeks, padding the final week if needed.
    weeks = []
    for start in range(0, len(days), 7):
        week = days[start : start + 7]
        if len(week) < 7:
            week += [{"date": "", "count": 0, "level": 0}] * (7 - len(week))
        weeks.append(week)

    week_count = len(weeks)
    outer_radius = 342
    ring_width = 17
    ring_gap = 8
    inner_start = outer_radius - (7 * ring_width + 6 * ring_gap)
    angle_step = 360 / week_count
    gap_angle = min(1.6, angle_step * 0.16)

    frames = []
    # One frame per week creates a clear clockwise sweep; the last frame is fully populated.
    for reveal_week in range(week_count + 1):
        image = Image.new("RGB", CANVAS, BACKGROUND)
        draw = ImageDraw.Draw(image)

        # Faint guide rings keep the seven weekday tracks legible before they are revealed.
        for weekday in range(7):
            outer = inner_start + (6 - weekday) * (ring_width + ring_gap) + ring_width
            inner = outer - ring_width
            for week_index in range(week_count):
                start_angle = -90 + week_index * angle_step + gap_angle / 2
                end_angle = -90 + (week_index + 1) * angle_step - gap_angle / 2
                ring_segment(draw, inner, outer, start_angle, end_angle, EMPTY)

        # Replace the revealed cells with their real contribution intensity.
        for week_index in range(min(reveal_week, week_count)):
            start_angle = -90 + week_index * angle_step + gap_angle / 2
            end_angle = -90 + (week_index + 1) * angle_step - gap_angle / 2
            for weekday, day in enumerate(weeks[week_index]):
                outer = inner_start + (6 - weekday) * (ring_width + ring_gap) + ring_width
                inner = outer - ring_width
                level = max(0, min(4, int(day.get("level", 0))))
                ring_segment(draw, inner, outer, start_angle, end_angle, LEVEL_COLORS[level])

        # The sweep hand marks the current reveal position.
        if reveal_week < week_count:
            angle = -90 + reveal_week * angle_step
            start = polar(122, angle)
            end = polar(outer_radius + 8, angle)
            draw.line((start, end), fill="#d95d00", width=3 * SCALE)
            tip = polar(outer_radius + 8, angle)
            r = 5 * SCALE
            draw.ellipse((tip[0] - r, tip[1] - r, tip[0] + r, tip[1] + r), fill="#d95d00")

        # Center label and total.
        total = f"{int(data.get('totalContributions', 0)):,}"
        centered_text(draw, 322, "CONTRIBUTIONS", font(13, True), MUTED)
        centered_text(draw, 352, total, font(54, True), TEXT)
        centered_text(draw, 426, "in the last year", font(15), MUTED)

        # Small weekday labels outside the rings.
        weekday_names = ["S", "M", "T", "W", "T", "F", "S"]
        for weekday, label in enumerate(weekday_names):
            angle = -90 + weekday * (360 / 7)
            # Labels are intentionally subtle; weekday order is also documented below.
            pos = polar(outer_radius + 27, angle)
            box = draw.textbbox((0, 0), label, font=font(11, True))
            draw.text((pos[0] - (box[2] - box[0]) / 2, pos[1] - (box[3] - box[1]) / 2), label, font=font(11, True), fill=MUTED)

        centered_text(draw, 785, f"@{data['username']}", font(17, True), TEXT)
        centered_text(draw, 812, "SUN  MON  TUE  WED  THU  FRI  SAT", font(10), MUTED)

        # Resize after drawing for smoother edges and smaller output.
        frames.append(image.resize((WIDTH, HEIGHT), Image.Resampling.LANCZOS))

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    frames[0].save(
        OUTPUT_FILE,
        save_all=True,
        append_images=frames[1:],
        duration=85,
        loop=0,
        optimize=True,
        disposal=2,
    )
    print(f"Created {OUTPUT_FILE} with {len(frames)} animation frames.")


if __name__ == "__main__":
    main()

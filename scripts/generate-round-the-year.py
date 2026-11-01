#!/usr/bin/env python3
"""Generate the Round the Year circular contribution calendar (GIF + PNG)."""
import json, math
from pathlib import Path
from datetime import date
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
data = json.loads((ROOT / "data/github.json").read_text(encoding="utf-8"))
days = data["days"]
weeks = [days[i:i+7] for i in range(0, len(days), 7)]
while len(weeks[-1]) < 7:
    weeks[-1].append({"date": "", "count": 0, "level": 0})

W, H, SCALE = 1920, 1080, 2
CW, CH = W*SCALE, H*SCALE
BG, TEXT, MUTED = "#f4f4f1", "#151515", "#70747a"
COLORS = ["#e9ecef", "#a5e6b4", "#62ce83", "#2eaa5b", "#167a3b"]
CX, CY, OUTER = 650*SCALE, 615*SCALE, 345
RING_W, RING_GAP = 23, 7
INNER = OUTER - (7*RING_W + 6*RING_GAP)
STEP = 360 / len(weeks)
GAP = min(1.05, STEP*0.18)

def font(size, serif=False, bold=False):
    paths = (["/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf"] if serif else
             ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else
              "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"])
    for path in paths:
        try: return ImageFont.truetype(path, size*SCALE)
        except OSError: pass
    return ImageFont.load_default()

def polar(radius, angle):
    a = math.radians(angle)
    return CX + math.cos(a)*radius*SCALE, CY + math.sin(a)*radius*SCALE

def curved_tile(draw, inner, outer, a0, a1, color):
    # Sample the outer and inner arcs to create a curved annular-sector tile.
    points = []
    steps = max(4, int(abs(a1-a0)*2))
    for i in range(steps+1):
        points.append(polar(outer, a0+(a1-a0)*i/steps))
    for i in range(steps, -1, -1):
        points.append(polar(inner, a0+(a1-a0)*i/steps))
    draw.polygon(points, fill=color)

months = {}
for i, day in enumerate(days):
    if day.get("date"):
        dt = date.fromisoformat(day["date"])
        if dt.day == 1:
            months[dt.strftime("%b").upper()] = -90 + (i/7)*STEP

def render(revealed):
    image = Image.new("RGB", (CW, CH), BG)
    draw = ImageDraw.Draw(image)
    draw.text((160*SCALE, 30*SCALE), "04", font=font(19), fill=MUTED)
    draw.text((300*SCALE, 8*SCALE), "Round the year", font=font(62, serif=True), fill=TEXT)
    draw.text((820*SCALE, 40*SCALE),
              "The same calendar wrapped into a ring: a ring per weekday, a spoke per week,",
              font=font(25), fill="#68717a")
    draw.text((820*SCALE, 82*SCALE), "read by a hand that sweeps the whole year.",
              font=font(25), fill="#68717a")
    draw.rounded_rectangle((0,170*SCALE,1920*SCALE,1050*SCALE),
                           radius=24*SCALE, fill="#ffffff", outline="#e4e4e4", width=2*SCALE)

    for wi, week in enumerate(weeks):
        a0 = -90 + wi*STEP + GAP/2
        a1 = -90 + (wi+1)*STEP - GAP/2
        for weekday in range(7):
            outer = OUTER - (6-weekday)*(RING_W+RING_GAP)
            inner = outer - RING_W
            level = int(week[weekday].get("level", 0)) if wi < revealed else 0
            curved_tile(draw, inner, outer, a0, a1, COLORS[max(0,min(4,level))])

    for label, angle in months.items():
        x, y = polar(OUTER+42, angle)
        f = font(18, bold=True)
        box = draw.textbbox((0,0), label, font=f)
        draw.text((x-(box[2]-box[0])/2, y-(box[3]-box[1])/2),
                  label, font=f, fill="#777b80")

    if revealed < len(weeks):
        angle = -90 + revealed*STEP
        tip = polar(OUTER+8, angle)
        draw.line((polar(INNER-18,angle),tip), fill="#268d50", width=3*SCALE)
        r = 5*SCALE
        draw.ellipse((tip[0]-r,tip[1]-r,tip[0]+r,tip[1]+r), fill="#268d50")

    total = f"{int(data.get('totalContributions',0)):,}"
    draw.text((1190*SCALE,500*SCALE), total, font=font(112,serif=True), fill=TEXT)
    draw.text((1190*SCALE,620*SCALE), "CONTRIBUTIONS", font=font(20,bold=True), fill=MUTED)
    first = next((x["date"] for x in days if x.get("date")), "")
    last = next((x["date"] for x in reversed(days) if x.get("date")), "")
    period = f"{date.fromisoformat(first).strftime('%b %Y').upper()}  TO  {date.fromisoformat(last).strftime('%b %Y').upper()}"
    draw.text((1190*SCALE,660*SCALE), period, font=font(19), fill=MUTED)
    draw.text((1190*SCALE,790*SCALE), "One curved tile per day", font=font(20), fill="#64696e")
    draw.text((1190*SCALE,830*SCALE), f"Seven weekday rings · {len(weeks)} weekly spokes",
              font=font(17), fill="#85898d")
    draw.rounded_rectangle((1700*SCALE,965*SCALE,1890*SCALE,1025*SCALE),
                           radius=12*SCALE, outline="#e1e1e1", width=2*SCALE)
    draw.text((1720*SCALE,980*SCALE), "↻  REPLAY", font=font(17,bold=True), fill="#777b80")
    return image.resize((W,H), Image.Resampling.LANCZOS)

frames = [render(i) for i in range(0, len(weeks)+1, 2)]
if len(weeks) % 2:
    frames.append(render(len(weeks)))
frames.append(render(len(weeks)))
assets = ROOT / "assets"
assets.mkdir(exist_ok=True)
gif = assets / "round-the-year.gif"
png = assets / "round-the-year-v1.0.png"
# Quantize frames to keep the looping GIF lightweight.
palette_frames = [frame.quantize(colors=96, method=Image.Quantize.MEDIANCUT) for frame in frames]
palette_frames[0].save(gif, save_all=True, append_images=palette_frames[1:],
                       duration=95, loop=0, optimize=True, disposal=2)
render(len(weeks)).save(png, optimize=True)
print(f"Created {gif} and {png} ({len(frames)} frames).")

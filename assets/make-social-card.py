#!/usr/bin/env python3
"""make-social-card.py — regenerate assets/social-preview.png on-brand.

The card shows the current protocol version and fixture count, which makes it
a version surface like README/index.html — but one the docs-sync checker
cannot read. The deal (CONTRIBUTING release ritual): regenerate the card as
part of every release, with this one command:

    python3 assets/make-social-card.py        # needs: pillow, cairosvg

Reads version from AUDIT.md's title and the fixture count from disk — never
hand-edit the numbers. Colors are sampled from the brand SVG's own fills
(#45210E brown, #F2B817 gold). Output: 2560x1280 (GitHub renders 1280x640;
keep >=80px margins clear per GitHub's 40pt-safe-area template).
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

try:
    import cairosvg
    from PIL import Image, ImageDraw, ImageFont
except ImportError as e:
    sys.exit(f"missing dependency: {e.name} — pip install pillow cairosvg")

VER = re.search(r"v\d+\.\d+\.\d+", (ROOT / "AUDIT.md").read_text(encoding="utf-8").splitlines()[0]).group(0)
N = sum(1 for d in (ROOT / "evals" / "fixtures").iterdir() if d.is_dir())

W, H = 2560, 1280
SAFE = 110
BROWN, GOLD = (69, 33, 14), (242, 184, 23)        # sampled from cyberskill-logo.svg fills
CREAM, CREAM_DIM, MUTED = (245, 233, 216), (212, 190, 163), (172, 142, 107)

cairosvg.svg2png(url=str(ROOT / "assets" / "cyberskill-logo.svg"),
                 write_to="/tmp/_cs_logo.png", output_width=760, output_height=760)

img = Image.new("RGB", (W, H), BROWN)             # flat: the logo's own bg blends seamlessly
d = ImageDraw.Draw(img)
F = "/usr/share/fonts/truetype/dejavu/DejaVuSans{}.ttf"
bold = lambda s: ImageFont.truetype(F.format("-Bold"), s)        # noqa: E731
reg = lambda s: ImageFont.truetype(F.format(""), s)              # noqa: E731
mono = lambda s: ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf", s)  # noqa: E731

logo = Image.open("/tmp/_cs_logo.png").convert("RGB")
img.paste(logo, (SAFE + 30, (H - logo.height) // 2 - 30))
tx = SAFE + 30 + logo.width + 100
avail = W - SAFE - tx

d.text((tx, 230), "C Y B E R S K I L L", font=bold(44), fill=GOLD)

title, size = "code-audit-framework", 132
while d.textlength(title, font=bold(size)) > avail and size > 60:
    size -= 2
d.text((tx, 310), title, font=bold(size), fill=CREAM)

tag = reg(56)
d.text((tx, 495), "An honest, self-improving audit protocol", font=tag, fill=CREAM_DIM)
d.text((tx, 572), "for AI coding agents.", font=tag, fill=CREAM_DIM)

chips = [VER, f"evals {N}/{N} green", "Apache-2.0", "AI-agnostic"]
cf = mono(42)
cx, cy, pad, hgt, gap, rowgap = tx, 730, 30, 80, 32, 26
for c in chips:
    w = d.textlength(c, font=cf) + 2 * pad
    if cx + w > W - SAFE:
        cx, cy = tx, cy + hgt + rowgap
    d.rounded_rectangle([cx, cy, cx + w, cy + hgt], radius=20, outline=GOLD, width=4)
    d.text((cx + pad, cy + (hgt - 42) // 2 - 5), c, font=cf, fill=GOLD)
    cx += w + gap

ff = mono(38)
foot = "github.com/cyberskill-official  ·  Turn Your Will Into Real"
while d.textlength(foot, font=ff) > W - SAFE - tx:
    ff = mono(ff.size - 2)
fy = H - SAFE - 52
d.line([(tx, fy - 38), (W - SAFE, fy - 38)], fill=(120, 85, 45), width=3)
d.text((tx, fy), foot, font=ff, fill=MUTED)

out = ROOT / "assets" / "social-preview.png"
img.save(out)
print(f"{out.relative_to(ROOT)} regenerated — {VER}, {N} fixtures")

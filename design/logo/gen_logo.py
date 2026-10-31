#!/usr/bin/env python3
"""SLIC2PORT-FXS logo generator.
All marks are single-colour geometric vector shapes (no hairlines, no gradients)
so they work as 1-colour PCB silkscreen and as case embossing.
Canvas: 240x240 for marks.
"""
import math
import os

OUT = os.path.dirname(os.path.abspath(__file__))
os.makedirs(OUT, exist_ok=True)


def rr(x, y, w, h, r):
    """Rounded-rect path."""
    return (
        f"M{x + r:.1f},{y:.1f} L{x + w - r:.1f},{y:.1f} "
        f"A{r:.1f},{r:.1f} 0 0 1 {x + w:.1f},{y + r:.1f} "
        f"L{x + w:.1f},{y + h - r:.1f} A{r:.1f},{r:.1f} 0 0 1 {x + w - r:.1f},{y + h:.1f} "
        f"L{x + r:.1f},{y + h:.1f} A{r:.1f},{r:.1f} 0 0 1 {x:.1f},{y + h - r:.1f} "
        f"L{x:.1f},{y + r:.1f} A{r:.1f},{r:.1f} 0 0 1 {x + r:.1f},{y:.1f} Z"
    )


def sine_path(x0, x1, yc, amp, periods, n=72):
    pts = []
    for i in range(n + 1):
        t = i / n
        x = x0 + (x1 - x0) * t
        y = yc - amp * math.sin(2 * math.pi * periods * t)
        pts.append((x, y))
    d = f"M{pts[0][0]:.1f},{pts[0][1]:.1f} "
    d += " ".join(f"L{x:.1f},{y:.1f}" for x, y in pts[1:])
    return d


def arc_pts(cx, cy, r, a0, a1, n=48):
    pts = []
    for i in range(n + 1):
        a = math.radians(a0 + (a1 - a0) * i / n)
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def pts_d(pts, close=False):
    d = f"M{pts[0][0]:.1f},{pts[0][1]:.1f} "
    d += " ".join(f"L{x:.1f},{y:.1f}" for x, y in pts[1:])
    return d + (" Z" if close else "")


def pt(cx, cy, r, deg):
    a = math.radians(deg)
    return (cx + r * math.cos(a), cy + r * math.sin(a))


# ---------------------------------------------------------------- concept A
def mark_a(c):
    """RJ11 jack port (front) + signal wave below."""
    ring = rr(60, 24, 120, 120, 18) + " " + rr(79, 43, 82, 82, 10)
    pins = ""
    for i in range(4):  # 4 gold contacts hanging from the top of the port
        x = 90.5 + i * 17
        pins += f'<rect x="{x:.1f}" y="43" width="9" height="36" rx="3" fill="{c}"/>'
    wave = sine_path(34, 206, 194, 15, 1.5)
    return (
        f'<path fill-rule="evenodd" fill="{c}" d="{ring}"/>'
        + pins
        + f'<path d="{wave}" stroke="{c}" stroke-width="15" fill="none" stroke-linecap="round"/>'
    )


# ---------------------------------------------------------------- concept B
def mark_b(c):
    """Telephone handset (annular sector + earpiece blocks) + ringing arcs."""
    cx, cy, ro, ri = 112, 140, 92, 58
    outer = arc_pts(cx, cy, ro, 193, 347)
    inner = arc_pts(cx, cy, ri, 347, 193)
    body = pts_d(outer) + " " + " ".join(f"L{x:.1f},{y:.1f}" for x, y in inner) + " Z"
    rm = (ro + ri) / 2
    blocks = ""
    for ang in (193, 347):  # earpiece / mouthpiece blocks, radial orientation
        ex, ey = pt(cx, cy, rm, ang)
        blocks += (
            f'<g transform="rotate({ang + 90:.0f} {ex:.1f} {ey:.1f})">'
            f'<rect x="{ex - 19:.1f}" y="{ey - 24:.1f}" width="38" height="48" rx="11" fill="{c}"/></g>'
        )
    waves = ""
    for r in (24, 45):
        waves += (
            f'<path d="{pts_d(arc_pts(192, 100, r, 252, 330))}" stroke="{c}" '
            f'stroke-width="12" fill="none" stroke-linecap="round"/>'
        )
    return f'<path fill="{c}" d="{body}"/>' + blocks + waves


# ---------------------------------------------------------------- concept C
def mark_c(c):
    """Two modular ports linked by an S-wave (2-port FXS bridge)."""

    def port(cx):
        d = rr(cx - 33, 87, 66, 66, 12)
        for dx in (-20.5, -4.5, 11.5):  # 3 contact slits knocked out of the face
            d += " " + rr(cx + dx, 100, 9, 27, 3)
        return f'<path fill-rule="evenodd" fill="{c}" d="{d}"/>'

    link = sine_path(90, 150, 120, 16, 1.0)
    return (
        port(57)
        + port(183)
        + f'<path d="{link}" stroke="{c}" stroke-width="14" fill="none" stroke-linecap="round"/>'
    )


MARKS = {"a": mark_a, "b": mark_b, "c": mark_c}
NAMES = {
    "a": "JACK &amp; WAVE",
    "b": "HANDSET RING",
    "c": "TWO PORTS / S-LINK",
}


def svg_doc(body, w=240, h=240, bg=None):
    bgrect = f'<rect width="{w}" height="{h}" fill="{bg}"/>' if bg else ""
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
        f'viewBox="0 0 {w} {h}">{bgrect}{body}</svg>\n'
    )


def write(name, content):
    with open(os.path.join(OUT, name), "w") as f:
        f.write(content)
    print("wrote", name)


for key, fn in MARKS.items():
    write(f"logo-{key}.svg", svg_doc(fn("#000000")))
    write(f"logo-{key}-on-black.svg", svg_doc(fn("#FFFFFF"), bg="#000000"))
    write(f"logo-{key}-on-white.svg", svg_doc(fn("#000000"), bg="#FFFFFF"))

# ---------------------------------------------------------------- wordmark (concept A lockup)
wm_body = (
    mark_a("#000000")
    + '<text x="282" y="128" font-family="Helvetica, Arial, sans-serif" '
      'font-size="78" font-weight="700" letter-spacing="0" fill="#000000">SLIC2PORT-FXS</text>'
    + '<text x="286" y="176" font-family="Helvetica, Arial, sans-serif" '
      'font-size="28" font-weight="400" letter-spacing="5" fill="#000000">2-PORT FXS PSEUDO EXCHANGE</text>'
)
write("logo-wordmark.svg", svg_doc(wm_body, w=1500, h=240))
wm_body_w = wm_body.replace("#000000", "#FFFFFF")
write("logo-wordmark-on-black.svg", svg_doc(wm_body_w, w=1500, h=240, bg="#000000"))
write("logo-wordmark-on-white.svg", svg_doc(wm_body, w=1500, h=240, bg="#FFFFFF"))

# ---------------------------------------------------------------- comparison sheet
tiles = []
label = {}
for i, key in enumerate(("a", "b", "c")):
    y = 20 + i * 360
    for j, (fg, bg) in enumerate((("#FFFFFF", "#000000"), ("#000000", "#FFFFFF"))):
        x = 20 + j * 480
        tiles.append(f'<rect x="{x}" y="{y}" width="460" height="340" fill="{bg}"/>')
        tiles.append(
            f'<g transform="translate({x + 110},{y + 50})">{MARKS[key](fg)}</g>'
        )
        tiles.append(
            f'<text x="{x + 18}" y="{y + 40}" font-family="Helvetica, Arial, sans-serif" '
            f'font-size="30" font-weight="700" fill="{fg}">{key.upper()} — {NAMES[key]}</text>'
        )
sheet = svg_doc("".join(tiles), w=980, h=1120, bg="#808080")
write("logo-compare.svg", sheet)
print("done")

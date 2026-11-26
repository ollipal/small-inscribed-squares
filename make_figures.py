#!/usr/bin/env python3
"""Draw the figures from the exact data: SVG for the README, TikZ for the paper.

    python3 make_figures.py        writes figures/*.svg and paper/src/fig_*.tex
"""
import os
import re
from fractions import Fraction as F
import verify

HERE = os.path.dirname(os.path.abspath(__file__))
STYLE = {  # name: (stroke, fill, fill opacity, dash, line width)
    "curve": ("#111111", None, 0, None, 1.6),
    "square": ("#d1342f", "#d1342f", 0.20, None, 1.4),
    "disc": ("#2a7de1", "#2a7de1", 0.12, None, 1.2),
    "outer": ("#2a7de1", None, 0, (7, 6), 1.2),
    "lost": ("#b9770e", None, 0, (9, 6), 1.5),
    "dot": (None, "#111111", 1, None, 0),
    "loose": (None, "#b9770e", 1, None, 0),
}


class Figure:
    """A drawing 1000 units wide, made of panels that each show a window of the plane."""

    def __init__(self, height):
        self.height, self.svg, self.tikz, self.clips = height, [], [], 0

    def panel(self, box, window):
        """box = (x, y, size) on the page; window = (x0, y0, x1, y1) in the plane."""
        bx, by, size = box
        x0, y0, x1, y1 = window
        k = size / max(x1 - x0, y1 - y0)
        to_page = lambda p: (bx + (float(p[0]) - x0) * k, by + (y1 - float(p[1])) * k)
        return Panel(self, to_page, k, (bx, by, (x1 - x0) * k, (y1 - y0) * k))

    def text(self, x, y, s):
        self.svg.append(f'<text x="{x:.1f}" y="{y:.1f}" font-family="sans-serif" font-size="26" '
                        f'text-anchor="middle" fill="#333">{s}</text>')
        self.tikz.append(f"\\node[font=\\small] at ({x:.1f},{-y:.1f}) {{{s.replace('=', '$=$')}}};")

    def save(self, name, width_cm=12.5):
        svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 {self.height}" width="760">\n'
               f'<rect width="1000" height="{self.height}" fill="white"/>\n' + "\n".join(self.svg) + "\n</svg>\n")
        open(os.path.join(HERE, "figures", name + ".svg"), "w").write(svg)
        unit = width_cm / 1000
        body = re.sub(r"@([\d.]+)@", lambda w: f"{float(w.group(1)) * unit * 1.25:.4f}cm", "\n".join(self.tikz))
        tikz = f"\\begin{{tikzpicture}}[x={unit:.5f}cm,y={unit:.5f}cm,line join=round]\n{body}\n\\end{{tikzpicture}}\n"
        open(os.path.join(HERE, "paper", "src", "fig_" + name + ".tex"), "w").write(tikz)


class Panel:
    def __init__(self, fig, to_page, k, rect):
        self.fig, self.to_page, self.k, self.rect = fig, to_page, k, rect
        fig.clips += 1
        self.clip = f"clip{id(fig) % 10000}_{fig.clips}"
        x, y, w, h = rect
        fig.svg.append(f'<clipPath id="{self.clip}"><rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}"/></clipPath>')

    def _emit(self, svg_shape, tikz_path, style):
        stroke, fill, opacity, dash, width = STYLE[style]
        attrs = f'stroke="{stroke or "none"}" stroke-width="{width}" stroke-linejoin="round" '
        attrs += f'fill="{fill}" fill-opacity="{opacity}" ' if fill else 'fill="none" '
        if dash:
            attrs += f'stroke-dasharray="{dash[0]} {dash[1]}" '
        self.fig.svg.append(f'<g clip-path="url(#{self.clip})"><{svg_shape} {attrs}/></g>')
        opts = [f"line width=@{width}@"] if stroke else []
        if stroke:
            opts.append("draw=" + style + "C")
        if fill:
            opts.append(f"fill={style}C, fill opacity={opacity}")
        if dash:
            opts.append("dashed")
        x, y, w, h = self.rect
        self.fig.tikz.append(f"\\begin{{scope}}\\clip ({x:.1f},{-y:.1f}) rectangle ({x + w:.1f},{-(y + h):.1f});"
                             f"\\path[{', '.join(opts)}] {tikz_path};\\end{{scope}}")

    def polygon(self, points, style):
        pts = [self.to_page(p) for p in points]
        self._emit('polygon points="' + " ".join(f"{x:.2f},{y:.2f}" for x, y in pts) + '"',
                   " -- ".join(f"({x:.2f},{-y:.2f})" for x, y in pts) + " -- cycle", style)

    def circle(self, centre, radius, style, on_page=False):
        (x, y), r = self.to_page(centre), (radius if on_page else float(radius) * self.k)
        self._emit(f'circle cx="{x:.2f}" cy="{y:.2f}" r="{r:.2f}"', f"({x:.2f},{-y:.2f}) circle ({r:.2f})", style)


def bounds(points, pad=0.05):
    xs, ys = [float(p[0]) for p in points], [float(p[1]) for p in points]
    size = max(max(xs) - min(xs), max(ys) - min(ys))
    cx, cy = (max(xs) + min(xs)) / 2, (max(ys) + min(ys)) / 2
    h = size * (0.5 + pad)
    return (cx - h, cy - h, cx + h, cy + h)


def root(x):
    return float(x) ** 0.5


def pentagon():
    V = verify.polygon(verify.PENTAGON)
    c = (F(16, 3), F(16, 3))
    fig = Figure(520)
    p = fig.panel((250, 10, 500), bounds(V))
    p.circle(c, root(verify.inner_radius_squared(V, c)), "disc")
    p.polygon(verify.inscribed_squares(V)[0][0][1], "square")
    p.polygon(V, "curve")
    for v in V:
        p.circle(v, 6, "dot", on_page=True)
    fig.save("pentagon", 8)


def largest_circle_near(V, start):
    """Centre of the largest circle inside the polygon, found by stepping uphill from `start`.
    Any inside point gives a valid circle; this just makes the drawn one touch the walls."""
    c, best, step = start, verify.inner_radius_squared(V, start), F(4)
    while step > F(1, 200):
        moves = [(c[0] + dx * step, c[1] + dy * step) for dx in (-1, 0, 1) for dy in (-1, 0, 1) if dx or dy]
        r2, q = max((verify.inner_radius_squared(V, q), q) for q in moves if verify.is_inside(V, q))
        if r2 > best:
            c, best = q, r2
        else:
            step /= 2
    return c


def rooms():
    fig = Figure(390)
    for k, m in enumerate((20, 40, 80)):
        V = verify.rooms(m)
        p = fig.panel((15 + 330 * k, 10, 310), bounds(V))
        c = largest_circle_near(V, (F(3 * m), F(-4 * m)))      # stays in the lower-right room
        p.circle(c, root(verify.inner_radius_squared(V, c)), "disc")
        p.polygon(verify.inscribed_squares(V)[0][0][1], "square")
        p.polygon(V, "curve")
        fig.text(170 + 330 * k, 365, f"m = {m}")
    fig.save("rooms")


ROOMS = {"upper-left": [10, 11, 12, 0, 1], "lower-left": [1, 2, 3, 4, 5], "lower-right": [5, 6, 7, 8, 9]}


def doorways():
    """Each room with its doorway walled up has room-sized squares; all use the doorway wall."""
    V = verify.rooms(20)
    lost = []
    for name, corners in ROOMS.items():
        room = [V[i] for i in corners]                  # its last side closes the doorway
        squares, undecided = verify.inscribed_squares(room)
        door = (room[-1], room[0])
        assert not undecided
        for side2, sq in squares:
            on_door = [P for P in sq if (P[0] - door[0][0]) * (door[1][1] - door[0][1])
                       == (P[1] - door[0][1]) * (door[1][0] - door[0][0])]
            assert on_door, "a square that does not use the doorway"
        print(f"  {name} room, doorway closed: {len(squares)} square(s), each with a corner on the doorway wall")
        lost.append((squares[0][1], on_door[0]))
    fig = Figure(480)
    left = fig.panel((20, 10, 460), bounds(V))
    right = fig.panel((530, 10, 460), (-36, -32, 36, 40))
    for sq, corner in lost:
        left.polygon(sq, "lost")
        right.polygon(sq, "lost")
        right.circle(corner, 9, "loose", on_page=True)
    left.polygon(V, "curve")
    right.polygon(V, "curve")
    fig.save("doorways")


def ring(index, name):
    """A ring example with its two circles and all its inscribed squares."""
    _, corners, centre = verify.RING_LOOPS[index]
    V, c = verify.polygon(corners), verify.polygon(centre)[0]
    r, R = root(verify.inner_radius_squared(V, c)), root(verify.outer_radius_squared(V, c))
    fig = Figure(560)
    p = fig.panel((230, 10, 540), (float(c[0]) - R * 1.04, float(c[1]) - R * 1.04, float(c[0]) + R * 1.04, float(c[1]) + R * 1.04))
    p.circle(c, r, "disc")
    p.circle(c, R, "outer")
    for _, square in verify.inscribed_squares(V)[0]:
        p.polygon(square, "square")
    p.polygon(V, "curve")
    for v in V:
        p.circle(v, 6, "dot", on_page=True)
    fig.save(name, 8.5)


if __name__ == "__main__":
    pentagon(); rooms(); doorways(); ring(2, "ring12"); ring(3, "ring16")
    print("figures written")

#!/usr/bin/env python3
"""The trapped ball: a conjecture, and the numbers behind it.

For a polygon, roll a ball of radius r around inside it. A small ball can go
everywhere it fits. Past some radius the ball is trapped: there are two
places it fits that it cannot roll between. Call the largest radius at which
that has not yet happened r*. If the ball is never trapped, r* is simply the
radius of the largest ball that fits (the inradius, rho).

Conjecture: every simple polygon has an inscribed square of side at least
sqrt(2) * r*.

This is NOT proved. See paper/conjecture.pdf for what was tried. This script prints
the table there:  python3 trapped_ball.py          (about a minute)
                  python3 trapped_ball.py "x,y;x,y;..."   one polygon
                  python3 trapped_ball.py --figure        redraw figures/trapped_ball.svg

The squares come from verify.py (exact). rho and r* are floating point.
"""
import math
import sys

import verify


def depth(V, p):
    """Distance from p to the boundary of the polygon V."""
    best = float("inf")
    for i in range(len(V)):
        (ax, ay), (bx, by) = V[i], V[(i + 1) % len(V)]
        dx, dy = bx - ax, by - ay
        u = max(0.0, min(1.0, ((p[0] - ax) * dx + (p[1] - ay) * dy) / (dx * dx + dy * dy)))
        best = min(best, math.hypot(p[0] - ax - u * dx, p[1] - ay - u * dy))
    return best


def inside(V, p):
    hit = False
    for i in range(len(V)):
        (ax, ay), (bx, by) = V[i], V[i - 1]
        if (ay > p[1]) != (by > p[1]) and p[0] < (bx - ax) * (p[1] - ay) / (by - ay) + ax:
            hit = not hit
    return hit


def deepest(V, region=None, grid=48):
    """Largest depth (measured in V) over the points of `region`, a polygon
    inside V (by default V itself), and where it is reached. A coarse grid,
    then a local climb."""
    region = region or V
    xs, ys = [p[0] for p in region], [p[1] for p in region]
    x0, y0, w, h = min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys)
    best, at = -1.0, None
    for i in range(grid):
        for j in range(grid):
            p = (x0 + (i + 0.5) * w / grid, y0 + (j + 0.5) * h / grid)
            if inside(region, p):
                d = depth(V, p)
                if d > best:
                    best, at = d, p
    if at is None:
        return 0.0, None
    step = max(w, h) / grid
    while step > 1e-9 * max(w, h):
        moved = False
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1)):
            p = (at[0] + dx * step, at[1] + dy * step)
            if inside(region, p):
                d = depth(V, p)
                if d > best:
                    best, at, moved = d, p, True
        if not moved:
            step /= 2
    return best, at


def is_reflex(V, i, orientation):
    (ax, ay), (bx, by), (cx, cy) = V[i - 1], V[i], V[(i + 1) % len(V)]
    return ((bx - ax) * (cy - by) - (by - ay) * (cx - bx)) * orientation < 0


def pinches(V):
    """Places where an inward-shrinking copy of V can pull apart: segments
    from a reflex corner to another reflex corner, or to the nearest point of
    a side, with nothing of the boundary closer to their midpoint than their
    own ends. Yields (half length, first piece, second piece, segment)."""
    n = len(V)
    area = sum(V[i][0] * V[(i + 1) % n][1] - V[(i + 1) % n][0] * V[i][1] for i in range(n))
    orientation = 1 if area > 0 else -1
    reflex = [i for i in range(n) if is_reflex(V, i, orientation)]
    for i in reflex:
        targets = []
        for j in reflex:
            if j > i and j not in ((i + 1) % n, (i - 1) % n):
                targets.append((V[j], j, None))
        for e in range(n):
            if e in (i, (i - 1) % n):
                continue
            (ax, ay), (bx, by) = V[e], V[(e + 1) % n]
            dx, dy = bx - ax, by - ay
            u = ((V[i][0] - ax) * dx + (V[i][1] - ay) * dy) / (dx * dx + dy * dy)
            if 1e-9 < u < 1 - 1e-9:
                targets.append(((ax + u * dx, ay + u * dy), None, e))
        for q, j, e in targets:
            half = math.dist(V[i], q) / 2
            mid = ((V[i][0] + q[0]) / 2, (V[i][1] + q[1]) / 2)
            if half == 0 or not inside(V, mid) or depth(V, mid) < half * (1 - 1e-7):
                continue
            # Cut the polygon along the segment into its two pieces.
            if j is not None:
                a, b = sorted((i, j))
                one, two = V[a:b + 1], V[b:] + V[:a + 1]
            else:
                walk = [V[(i + k) % n] for k in range(n)]      # starts at corner i
                cut = (e - i) % n                               # side e joins walk[cut] and walk[cut + 1]
                one, two = walk[:cut + 1] + [q], [q] + walk[cut + 1:] + [walk[0]]
            yield half, one, two, (V[i], q)


def trapped_radius(V, details=False):
    """(rho, r*) for the polygon V, given as a list of (x, y) floats. With
    `details`, also where the largest ball sits and, if the ball is trapped,
    the pinch segment and the roomiest spot on each side of it."""
    rho, centre = deepest(V, grid=96)
    best, where = rho, None
    for half, one, two, segment in sorted(pinches(V), key=lambda t: t[0]):
        if half >= best:
            break
        # The ball is trapped here only if a bigger ball fits on both sides.
        (d1, p1), (d2, p2) = deepest(V, one), deepest(V, two)
        if d1 > half * (1 + 1e-6) and d2 > half * (1 + 1e-6):
            best, where = half, (segment, (d1, p1), (d2, p2))
    return (rho, best, centre, where) if details else (rho, best)


def report(name, text):
    exact = verify.polygon(text)
    squares, undecided = verify.inscribed_squares(exact)
    side = math.sqrt(squares[0][0])                 # verify.py lists the largest first
    V = [(float(x), float(y)) for x, y in exact]
    rho, rstar = trapped_radius(V)
    note = "never trapped" if rstar >= rho * (1 - 1e-9) else "trapped"
    flag = " *" if undecided else ""
    print(f"{name:<34}{len(V):>3} {len(squares):>4}{flag:<2} {side:>10.4f} {rho:>10.4f} {rstar:>10.4f}"
          f" {side / rho:>8.3f} {side / rstar:>8.4f}   {note}")
    return side / rstar


DUMBBELL = "-3,-1.2;-1,-1.3;-0.9,-0.35;1,-0.42;1.1,-1.4;3.2,-1.1;3,1.3;1.05,1.2;0.9,0.4;-1,0.33;-1.1,1.3;-3.1,1.1"

SHAPES = [
    ("regular pentagon", "0,1;-0.9511,0.309;-0.5878,-0.809;0.5878,-0.809;0.9511,0.309"),
    ("kite", "1,0;0.1,0.6;-1,0.05;0,-0.65"),
    ("dumbbell", DUMBBELL),
    ("pentagon of the paper's appendix", verify.PENTAGON),
    ("ring octagon", verify.RING_LOOPS[1][1]),
    ("Pochuev's 10-gon (x 1200)", "4114,-558;2022,1568;-1234,1006;-868,2516;-1089,2814;-3769,1169;-3459,81;141,-1348;571,-1449;1105,-485"),
    ("three rooms, m = 20", ";".join(f"{x},{y}" for x, y in verify.rooms(20))),
    ("three rooms, m = 40", ";".join(f"{x},{y}" for x, y in verify.rooms(40))),
    ("three rooms, m = 80", ";".join(f"{x},{y}" for x, y in verify.rooms(80))),
    ("blob at the circle's value",
     "-79.066,-37.606;-79.769,33.919;-62.798,96.286;82.518,98.308;82.852,-25.198;77.798,-34.745;78.464,-63.284;-100,-67.68"),
]


def figure(path):
    """Draws the dumbbell with its largest balls, its trapped ball, and its
    largest and smallest inscribed squares, as an SVG file."""
    exact = verify.polygon(DUMBBELL)
    squares, _ = verify.inscribed_squares(exact)
    V = [(float(x), float(y)) for x, y in exact]
    rho, rstar, centre, where = trapped_radius(V, details=True)
    (a, b), (d1, p1), (d2, p2) = where
    k, ox, oy = 100, 340, 170                       # pixels per unit, origin
    at = lambda p: (ox + k * float(p[0]), oy - k * float(p[1]))
    pts = lambda P: " ".join(f"{x:.1f},{y:.1f}" for x, y in map(at, P))
    circle = lambda p, r, cls: f'<circle cx="{at(p)[0]:.1f}" cy="{at(p)[1]:.1f}" r="{k * r:.1f}" class="{cls}"/>'
    mid = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 680 340" font-family="sans-serif" font-size="13">
<style>.shape{{fill:#eef5f1;stroke:#1f9d6b;stroke-width:2;stroke-linejoin:round}}
.big{{fill:none;stroke:#3d7bd9;stroke-width:1.6;stroke-dasharray:6 5}}
.stuck{{fill:#ff9f43;fill-opacity:.35;stroke:#d97706;stroke-width:1.8}}
.square{{fill:#d63b3b;fill-opacity:.12;stroke:#d63b3b;stroke-width:2}}
.small{{fill:none;stroke:#d63b3b;stroke-width:1.5;stroke-dasharray:4 3}}
text{{fill:#333}}</style>
<polygon points="{pts(V)}" class="shape"/>
{circle(p1, d1, "big")}{circle(p2, d2, "big")}
<polygon points="{pts(squares[0][1])}" class="square"/>
<polygon points="{pts(squares[-1][1])}" class="small"/>
{circle(mid, rstar, "stuck")}
<text x="20" y="328">dashed: largest balls that fit (radius {rho:.2f})</text>
<text x="300" y="328">orange: the largest ball that is not trapped (r* = {rstar:.2f})</text>
<text x="20" y="20">red: the largest inscribed square (side {math.sqrt(squares[0][0]):.2f}); dashed red: the smallest, at the pinch (side {math.sqrt(squares[-1][0]):.2f})</text>
</svg>
'''
    open(path, "w").write(svg)
    print("wrote", path)
    # The same picture for the paper, in TikZ.
    xy = lambda p: f"({float(p[0]):.4f},{float(p[1]):.4f})"
    path_of = lambda P: " -- ".join(xy(p) for p in P) + " -- cycle"
    tikz = f'''\\begin{{tikzpicture}}[x=1.9cm,y=1.9cm,line join=round]
\\path[draw=curveC, line width=0.8pt, fill=black!4] {path_of(V)};
\\path[draw=discC, dashed, line width=0.6pt] {xy(p1)} circle ({d1:.4f});
\\path[draw=discC, dashed, line width=0.6pt] {xy(p2)} circle ({d2:.4f});
\\path[draw=squareC, line width=0.8pt, fill=squareC, fill opacity=0.12] {path_of(squares[0][1])};
\\path[draw=squareC, dashed, line width=0.6pt] {path_of(squares[-1][1])};
\\path[draw=looseC, line width=0.8pt, fill=looseC, fill opacity=0.3] {xy(mid)} circle ({rstar:.4f});
\\end{{tikzpicture}}
'''
    open("paper/src/fig_trapped.tex", "w").write(tikz)
    print("wrote paper/src/fig_trapped.tex")


def main(args):
    if args and args[0] == "--figure":
        return figure("figures/trapped_ball.svg")
    print(f"{'shape':<34}{'n':>3} {'sq':>4}   {'S':>10} {'rho':>10} {'r*':>10} {'S/rho':>8} {'S/r*':>8}")
    shapes = [("polygon", args[0])] if args else SHAPES
    lowest = min(report(name, text) for name, text in shapes)
    print(f"\nsmallest S/r*: {lowest:.4f}   (sqrt 2 = {math.sqrt(2):.4f})")
    print("S: side of the largest inscribed square (exact). rho: largest ball that fits.")
    print("r*: largest ball that is not yet trapped.  * = verify.py could not rule out a sliding family.")


if __name__ == "__main__":
    main(sys.argv[1:])

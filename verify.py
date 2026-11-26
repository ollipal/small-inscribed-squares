#!/usr/bin/env python3
"""Find EVERY square inscribed in a polygon, exactly.  Python 3, no packages.

The idea.  Write a square as a corner p and a side vector v:

    corners:  p,   p + v,   p + v + Rv,   p + Rv        (R = quarter turn)

That is four unknown numbers (p has two, v has two).  Now pick four sides of the
polygon and ask that corner 0 lies on the line through the first side, corner 1
on the line through the second, and so on.  Each of these is ONE linear equation,
so we have four linear equations in four unknowns: generally exactly one
solution.  If its four corners really land on the four sides (not just on the
lines extended), we have found an inscribed square.

Every inscribed square arises this way for some choice of four sides, so trying
all choices finds them all.  All arithmetic is in exact fractions, so there is
no rounding and nothing is missed or invented.

    python3 verify.py               check every claim in the README (a few seconds)
    python3 verify.py --slow        also the 26- and 31-corner loops (about two minutes)
    python3 verify.py "0,0;4,0;4,3;0,3"      list the squares of your own polygon
"""
import os
import sys
from fractions import Fraction as F
from itertools import product


def reduce(rows):
    """Gauss-Jordan elimination with exact fractions. Returns (rank, reduced rows)."""
    M = [list(r) for r in rows]
    rank = 0
    for col in range(len(M[0])):
        pivot = next((r for r in range(rank, len(M)) if M[r][col] != 0), None)
        if pivot is None:
            continue
        M[rank], M[pivot] = M[pivot], M[rank]
        M[rank] = [x / M[rank][col] for x in M[rank]]
        for r in range(len(M)):
            if r != rank and M[r][col] != 0:
                M[r] = [x - M[r][col] * y for x, y in zip(M[r], M[rank])]
        rank += 1
    return rank, M


def inscribed_squares(V):
    """All inscribed squares of the polygon V (a list of exact points).

    Returns (squares, undecided).  Each square is (side squared, corners).
    `undecided` lists choices of four sides whose equations do not pin down a
    single square (this needs parallel sides); it must be empty for the answer
    to be complete, and it is empty for every polygon used here.
    """
    n = len(V)
    side = [(V[i], V[(i + 1) % n]) for i in range(n)]

    def equation(i, j):
        """Corner j of the square lies on the line through side i:  one row [.. | rhs]."""
        (ax, ay), (bx, by) = side[i]
        nx, ny = by - ay, ax - bx                      # a normal to the side
        rhs = nx * ax + ny * ay
        # corner j = p + C_j v,  with  Rv = (-v_y, v_x)
        v_part = [(0, 0), (nx, ny), (nx + ny, ny - nx), (ny, -nx)][j]
        return [nx, ny, v_part[0], v_part[1], rhs]

    def on_side(i, P):
        (ax, ay), (bx, by) = side[i]                   # P is already on the line
        return min(ax, bx) <= P[0] <= max(ax, bx) and min(ay, by) <= P[1] <= max(ay, by)

    squares, undecided = {}, []
    for sides in product(range(n), repeat=4):
        if sides[0] != min(sides):                     # each square has a labelling like this
            continue
        system = [equation(i, j) for j, i in enumerate(sides)]
        rank, M = reduce(system)
        if rank == 4 and all(M[k][k] == 1 for k in range(4)):
            px, py, vx, vy = (M[k][4] for k in range(4))
            if vx == 0 and vy == 0:
                continue                               # a single point is not a square
            corners = [(px, py), (px + vx, py + vy), (px + vx - vy, py + vy + vx), (px - vy, py + vx)]
            if all(on_side(i, P) for i, P in zip(sides, corners)):
                squares[frozenset(corners)] = (vx * vx + vy * vy, corners)
        elif rank == reduce([row[:4] for row in system])[0]:
            # Fewer than four independent equations, but they are consistent: a whole
            # family of solutions.  Harmless only if all of them have v = 0.
            forced = system + [[0, 0, 1, 0, 0], [0, 0, 0, 1, 0]]
            if reduce(forced)[0] != rank:
                undecided.append(sides)
        # otherwise the equations contradict each other: no square on these sides
    return sorted(squares.values(), key=lambda s: -s[0]), undecided


def is_simple(V):
    """True if the polygon does not touch or cross itself."""
    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    def within(p, a, b):
        return min(a[0], b[0]) <= p[0] <= max(a[0], b[0]) and min(a[1], b[1]) <= p[1] <= max(a[1], b[1])

    n = len(V)
    for i in range(n):
        for j in range(i + 2, n):
            if (j + 1) % n == i:
                continue                               # neighbouring sides share a corner
            a, b, c, d = V[i], V[(i + 1) % n], V[j], V[(j + 1) % n]
            d1, d2, d3, d4 = cross(c, d, a), cross(c, d, b), cross(a, b, c), cross(a, b, d)
            if d1 * d2 < 0 and d3 * d4 < 0:
                return False
            if (d1 == 0 and within(a, c, d)) or (d2 == 0 and within(b, c, d)) \
                    or (d3 == 0 and within(c, a, b)) or (d4 == 0 and within(d, a, b)):
                return False
    return True


def is_inside(V, c):
    n, inside = len(V), False
    for i in range(n):
        (ax, ay), (bx, by) = V[i], V[(i + 1) % n]
        if (ay > c[1]) != (by > c[1]) and c[0] < ax + (c[1] - ay) * (bx - ax) / (by - ay):
            inside = not inside
    return inside


def inner_radius_squared(V, c):
    """Exact squared distance from the point c to the nearest point of the polygon."""
    best = None
    for i in range(len(V)):
        (ax, ay), (bx, by) = V[i], V[(i + 1) % len(V)]
        dx, dy = bx - ax, by - ay
        t = max(F(0), min(F(1), ((c[0] - ax) * dx + (c[1] - ay) * dy) / (dx * dx + dy * dy)))
        d2 = (ax + t * dx - c[0]) ** 2 + (ay + t * dy - c[1]) ** 2
        best = d2 if best is None or d2 < best else best
    return best


def outer_radius_squared(V, c):
    return max((x - c[0]) ** 2 + (y - c[1]) ** 2 for x, y in V)


def polygon(text):
    return [tuple(F(v) for v in point.split(",")) for point in text.split(";") if point.strip()]


HERE = os.path.dirname(os.path.abspath(__file__))


def rooms(m, path=os.path.join(HERE, "data", "rooms13.txt")):
    """The three-room polygon P(m): corner = m*(x, y) + (dx, dy)."""
    rows = [list(map(int, line.split())) for line in open(path) if line.strip() and not line.startswith("#")]
    return [(F(m * x + dx), F(m * y + dy)) for x, y, dx, dy in rows]


# ---------------------------------------------------------------- the claims

PENTAGON = "1,2;3,5;8,0;7,7;0,8"
RING_LOOPS = [  # (name, corners, centre of the ring)
    ("pentagon", PENTAGON, "16/3,16/3"),
    ("8 corners", "-2,7;4,12;13,0;16,17;6,19;7,26;-1,21;-3,14", "49/5,129/10"),
    ("12 corners", "43,47;82,28;100,52;87,71;76,81;63,84;42,77;20,91;14,80;12,49;16,38;35,25", "641/10,3059/50"),
    ("16 corners", open(os.path.join(HERE, "data", "ring16.txt")).read().strip(), "-18/5,-4/5"),
    ("20 corners", open(os.path.join(HERE, "data", "ring20.txt")).read().strip(), "2/5,1/5"),
]
RING_SLOW = [
    ("26 corners", open(os.path.join(HERE, "data", "ring26.txt")).read().strip(), "1/10,1/10"),
    ("31 corners", open(os.path.join(HERE, "data", "ring31.txt")).read().strip(), "-25534433/10,8917955"),
]

failures = []


def check(ok, text):
    print(("  ok    " if ok else "  FAIL  ") + text)
    if not ok:
        failures.append(text)


def check_rooms(m):
    V = rooms(m)
    squares, undecided = inscribed_squares(V)
    centre = (F(3 * m), F(-4 * m))
    r2 = inner_radius_squared(V, centre)
    side2 = squares[0][0]
    print(f"three rooms, m = {m}")
    check(is_simple(V), "the outline does not cross itself")
    check(not undecided and len(squares) == 1, f"exactly {len(squares)} inscribed square, side {float(side2) ** 0.5:.3f}")
    check(is_inside(V, centre) and r2 >= (2 * m) ** 2, f"contains a circle of radius {2 * m}")
    print(f"        largest square / that circle's radius <= {float(side2) ** 0.5 / (2 * m):.4f}")


def check_ring(name, corners, centre):
    V, c = polygon(corners), polygon(centre)[0]
    squares, undecided = inscribed_squares(V)
    r2, R2 = inner_radius_squared(V, c), outer_radius_squared(V, c)
    side2 = squares[0][0]
    print(f"ring loop, {name}")
    check(is_simple(V) and is_inside(V, c), "a simple loop going once round the centre")
    check(not undecided, f"{len(squares)} inscribed square(s), all found")
    check(side2 < 2 * r2, f"largest square {float(side2) ** 0.5:.4f} is below the promised "
                          f"sqrt2 x inner radius = {float(2 * r2) ** 0.5:.4f}")
    print(f"        ring ratio outer/inner = {float(R2 / r2) ** 0.5:.7f}     (Matschke's limit is 2.4142136)")


def main(args):
    if args and not args[0].startswith("--"):          # the user's own polygon
        V = polygon(args[0])
        squares, undecided = inscribed_squares(V)
        print(f"{len(V)} corners, simple: {is_simple(V)}, inscribed squares: {len(squares)}")
        for side2, corners in squares:
            print(f"  side {float(side2) ** 0.5:.6f}  corners " + " ".join(f"({float(x):.4f},{float(y):.4f})" for x, y in corners))
        if undecided:
            print(f"  WARNING: {len(undecided)} choices of sides allow a sliding family of squares (parallel sides).")
        return

    print("pentagon")
    V = polygon(PENTAGON)
    squares, undecided = inscribed_squares(V)
    r2 = inner_radius_squared(V, (F(16, 3), F(16, 3)))
    check(is_simple(V) and not undecided and len(squares) == 1, "exactly one inscribed square")
    check(squares[0][0] < 2 * r2, f"its side {float(squares[0][0]) ** 0.5:.4f} is below sqrt2 x inradius "
                                  f"(circle radius {float(r2) ** 0.5:.4f}; ratio {float(squares[0][0] / r2) ** 0.5:.4f})")
    for m in (20, 40, 80, 100, 1000):
        check_rooms(m)
    for loop in RING_LOOPS + (RING_SLOW if "--slow" in args else []):
        check_ring(*loop)
    print("\nALL CHECKS PASSED" if not failures else f"\n{len(failures)} CHECK(S) FAILED")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main(sys.argv[1:])

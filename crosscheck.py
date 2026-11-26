#!/usr/bin/env python3
"""Check our polygons with someone else's code.

B. J. Schulz's repository https://github.com/HiroSakuraba/Toeplitz.-Round-peg contains two
exact programs written independently of this one: `maximum_square` (v243), which finds the
largest inscribed square of a rational polygon by a different method, and `census_polygon`
(v223), which lists every inscribed square. This script runs both on the polygons used here
and compares with verify.py: the number of squares and the exact largest side must agree.

    git clone https://github.com/HiroSakuraba/Toeplitz.-Round-peg
    python3 crosscheck.py Toeplitz.-Round-peg/code          # about four minutes

Agreement was confirmed at commit a529b5e of that repository. Add --slow to include the
62-corner loop (about 15 minutes; largest square only, the full census would take hours).
"""
import os
import sys
from fractions import Fraction as F

import verify

sys.path.insert(0, os.path.abspath(sys.argv[1]))
from polygon_orbit_census_v223 import pt, census_polygon      # noqa: E402
from big_peg_exact_v243 import maximum_square, contained_disk  # noqa: E402

cases = [("pentagon", verify.polygon(verify.PENTAGON), (F(16, 3), F(16, 3)), F(32, 9))]
for m in (20, 40, 80, 100, 171, 1000):
    cases.append((f"three rooms, m = {m}", verify.rooms(m), (F(3 * m), F(-4 * m)), F(4 * m * m)))
for name, corners, centre in verify.RING_LOOPS[1:] + ([verify.RING_62] if "--slow" in sys.argv else []):
    V, c = verify.polygon(corners), verify.polygon(centre)[0]
    cases.append((f"ring loop, {name}", V, c, verify.inner_radius_squared(V, c)))

all_agree = True
for name, V, centre, radius_squared in cases:
    ours, undecided = verify.inscribed_squares(V)
    P = tuple(pt(x, y) for x, y in V)
    same_largest = maximum_square(P).side_squared == ours[0][0]
    same_count = len(V) > 20 or census_polygon(P).count == len(ours)   # census skipped on the 62-gon
    disc = contained_disk(P, pt(*centre), radius_squared)
    agree = same_largest and same_count and disc and not undecided
    all_agree &= agree
    print(f"{'  ok  ' if agree else ' FAIL '} {name}: {len(ours)} square(s); largest side identical: {same_largest}; "
          f"count identical: {same_count}; disc confirmed: {disc}", flush=True)
print("\nBOTH PROGRAMS AGREE ON EVERY POLYGON" if all_agree else "\nDISAGREEMENT")
sys.exit(0 if all_agree else 1)

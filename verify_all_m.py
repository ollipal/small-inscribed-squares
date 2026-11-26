#!/usr/bin/env python3
"""Inscribed squares of a ONE-PARAMETER family of polygons, for ALL large m at once.

The family: vertex i = m * (x_i, y_i) + (dx_i, dy_i), with integer data. Every
quantity that decides whether four edges carry an inscribed square is then a
polynomial in m with rational coefficients, and its sign for large m is the sign
of its leading coefficient. This script computes those polynomials exactly, and
a threshold M0 beyond every real root of every one of them (located with Sturm
sequences, to within 1/64). For
every real m > M0 the set of inscribed squares is therefore described by the same
edge quadruples, with explicit rational-function coordinates.

It certifies, for all real m > M0:
  1. the polygon is simple;
  2. it contains a disc of radius R*m (centre c0*m + c1 supplied on the command line);
  3. the complete list of inscribed squares, and that each has side below a constant.

Method for squares: as in verify.py. A square is P0 = p, P1 = p + v,
P2 = p + v + Rv, P3 = p + Rv. For four edges (e0..e3), "P_j on the line of e_j" is
a 4x4 linear system A(m) x = b(m), x = (p, v). With D = det A:
  * D not identically zero: x = adj(A) b / D for every m that is not a root of D.
    Corner j lies on its closed segment iff 0 <= tau_j <= 1, tau_j = T_j / (D L_j),
    i.e. T_j D >= 0 and (D L_j - T_j) D >= 0  (L_j = squared edge length > 0).
  * D identically zero: the generic ranks of A and [A|b] over Q(m) decide between
    "no solution" and "a family"; a family is harmless iff it forces v = 0.
Ranks over Q(m) are computed by evaluating at more integer points than the degree
of any minor, which is exact: a polynomial of degree <= d vanishing at d + 1
points is zero.

Usage: verify_all_m.py SPEC --centre cx0,cy0,cx1,cy1 --radius R [--from M]
       --from M   only look for a threshold above M (default 1)
       --side S   the bound to prove on the side of every square (default: 0.5% above its limit)
"""
import sys, itertools, math
from fractions import Fraction as F

# ---------- polynomials in m, as coefficient lists (lowest degree first) ----------
def trim(p):
    while p and p[-1] == 0: p = p[:-1]
    return p
def padd(p, q):
    n = max(len(p), len(q)); return trim([(p[i] if i < len(p) else 0) + (q[i] if i < len(q) else 0) for i in range(n)])
def pneg(p): return [-c for c in p]
def psub(p, q): return padd(p, pneg(q))
def pmul(p, q):
    if not p or not q: return []
    r = [F(0)] * (len(p) + len(q) - 1)
    for i, a in enumerate(p):
        if a:
            for j, b in enumerate(q): r[i + j] += a * b
    return trim(r)
def pval(p, m):
    r = F(0)
    for c in reversed(p): r = r * m + c
    return r
def lead_sign(p): return 0 if not p else (1 if p[-1] > 0 else -1)
def root_bound(p):
    """Every real root of the non-zero polynomial p has |root| <= this (Cauchy)."""
    if len(p) <= 1: return F(0)
    return 1 + max(abs(c / p[-1]) for c in p[:-1])
def pdiff(p): return trim([i * c for i, c in enumerate(p)][1:])
def prem(a, b):
    """Remainder of a divided by b."""
    a = a[:]
    while len(a) >= len(b) and a:
        f, k = a[-1] / b[-1], len(a) - len(b)
        a = trim([c - f * b[i - k] if i >= k else c for i, c in enumerate(a)][:-1])
    return a
def shifted(p, a):
    """Coefficients of p(x + a)."""
    q = p[:]
    for i in range(len(q) - 1):
        for j in range(len(q) - 2, i - 1, -1): q[j] += a * q[j + 1]
    return q
def roots_above(p, a, chain=None):
    """Number of distinct real roots of p in (a, infinity), by Sturm's theorem (needs p(a) != 0)."""
    if chain is None: chain = sturm(p)
    def changes(signs):
        signs = [x for x in signs if x]
        return sum(1 for x, y in zip(signs, signs[1:]) if x != y)
    sgn = lambda v: (v > 0) - (v < 0)
    return changes([sgn(pval(q, a)) for q in chain]) - changes([lead_sign(q) for q in chain])
def sturm(p):
    chain = [p, pdiff(p)]
    while chain[-1]:
        chain.append(pneg(prem(chain[-2], chain[-1])))
    return chain[:-1]
def largest_root_bound(p, start):
    """A number B >= start such that p has no real root in (B, infinity); B is within 1/64 of
    the largest real root when that root exceeds start."""
    q = shifted(p, start)
    if all(c >= 0 for c in q) or all(c <= 0 for c in q):
        return start                                  # Descartes: no root beyond start
    chain = sturm(p)
    lo, hi = start, max(start, root_bound(p))
    while pval(p, lo) == 0: lo += F(1, 1024)
    if roots_above(p, lo, chain) == 0: return lo
    while hi - lo > F(1, 64):
        mid = (lo + hi) / 2
        while pval(p, mid) == 0: mid += F(1, 4096)
        if roots_above(p, mid, chain) > 0: lo = mid
        else: hi = mid
    return hi
def pstr(p): return " + ".join(f"{float(c):.6g}*m^{i}" for i, c in enumerate(p) if c) or "0"

def det(M):
    n = len(M)
    if n == 1: return M[0][0]
    if n == 2: return psub(pmul(M[0][0], M[1][1]), pmul(M[0][1], M[1][0]))
    total = []
    for j in range(n):
        if not M[0][j]: continue
        minor = [row[:j] + row[j+1:] for row in M[1:]]
        term = pmul(M[0][j], det(minor))
        total = padd(total, term) if j % 2 == 0 else psub(total, term)
    return total

def nrank(rows):
    M = [r[:] for r in rows]; rk = 0
    for col in range(len(M[0])):
        piv = next((r for r in range(rk, len(M)) if M[r][col] != 0), None)
        if piv is None: continue
        M[rk], M[piv] = M[piv], M[rk]
        for r in range(len(M)):
            if r != rk and M[r][col] != 0:
                f = M[r][col] / M[rk][col]
                M[r] = [x - f * y for x, y in zip(M[r], M[rk])]
        rk += 1
    return rk

class Family:
    def __init__(self, spec):
        self.V = [([F(dx), F(x)], [F(dy), F(y)]) for x, y, dx, dy in spec]   # each coordinate is a polynomial in m
        self.V = [(trim(a), trim(b)) for a, b in self.V]
        self.n = len(self.V)
        self.polys = {}              # every polynomial whose sign must stay constant
        self.bound, self.worst = F(0), "nothing"
    def need(self, p, why):
        """Record that the sign of p must be constant: push the threshold past its roots."""
        if len(p) > 1:
            self.polys.setdefault(tuple(c / p[-1] for c in p), why)
    def threshold(self, start):
        """Smallest bound found beyond which none of the recorded polynomials has a real root."""
        for key, why in self.polys.items():
            b = largest_root_bound(list(key), start)
            if b > self.bound: self.bound, self.worst = b, why
        return self.bound
    def edge(self, i):
        a, b = self.V[i], self.V[(i + 1) % self.n]
        d = (psub(b[0], a[0]), psub(b[1], a[1]))
        N = (d[1], pneg(d[0]))                       # normal
        c = padd(pmul(N[0], a[0]), pmul(N[1], a[1]))
        L = padd(pmul(d[0], d[0]), pmul(d[1], d[1]))
        return a, b, d, N, c, L

def main():
    args = sys.argv[1:]
    spec = [tuple(int(v) for v in l.split("#")[0].split()) for l in open(args[0]) if l.strip() and not l.strip().startswith("#")]
    spec = [r for r in spec if len(r) == 4]
    cx0, cy0, cx1, cy1 = (F(v) for v in args[args.index("--centre") + 1].split(","))
    R = F(args[args.index("--radius") + 1])
    start = F(args[args.index("--from") + 1]) if "--from" in args else F(1)
    fam = Family(spec); n = fam.n
    E = [fam.edge(i) for i in range(n)]
    print(f"family of {n}-gons: vertex_i = m*(x_i, y_i) + (dx_i, dy_i)")

    # ---------- 1. simplicity ----------
    def orient(p, q, r):   # cross(q - p, r - p)
        return psub(pmul(psub(q[0], p[0]), psub(r[1], p[1])), pmul(psub(q[1], p[1]), psub(r[0], p[0])))
    simple, degenerate = True, []
    for i in range(n):
        for j in range(i + 1, n):
            a, b = fam.V[i], fam.V[(i + 1) % n]; c, d = fam.V[j], fam.V[(j + 1) % n]
            if j == i + 1 or (i == 0 and j == n - 1):
                # adjacent edges share a vertex: they overlap only if collinear and folded back
                shared, p, q = (b, a, d) if j == i + 1 else (a, b, c)
                cr = orient(shared, p, q)
                fam.need(cr, f"adjacent edges {i},{j} collinear")
                if not cr: degenerate.append(("collinear adjacent", i, j))
                continue
            ds = [orient(c, d, a), orient(c, d, b), orient(a, b, c), orient(a, b, d)]
            for k, pol in enumerate(ds): fam.need(pol, f"edges {i},{j} orientation {k}")
            s = [lead_sign(pol) for pol in ds]
            if 0 in s: degenerate.append(("touching for all m", i, j)); continue
            if s[0] != s[1] and s[2] != s[3]: simple = False
    print(f"1. simple for all large m: {simple and not degenerate}" + (f"   DEGENERATE: {degenerate}" if degenerate else ""))

    # ---------- 2. inscribed disc ----------
    centre = ([cx1, cx0], [cy1, cy0])
    centre = (trim(centre[0]), trim(centre[1]))
    disc_ok = True
    Rm2 = [F(0), F(0), R * R]                            # (R m)^2
    for i in range(n):
        a, b, d, N, c, L = E[i]
        w = (psub(centre[0], a[0]), psub(centre[1], a[1]))
        t = padd(pmul(w[0], d[0]), pmul(w[1], d[1]))     # tau = t / L
        fam.need(t, f"disc: foot on edge {i} (low)"); fam.need(psub(L, t), f"disc: foot on edge {i} (high)")
        if lead_sign(t) < 0:   dist2_num, den = padd(pmul(w[0], w[0]), pmul(w[1], w[1])), [F(1)]          # nearest: a
        elif lead_sign(psub(L, t)) < 0:
            u = (psub(centre[0], b[0]), psub(centre[1], b[1])); dist2_num, den = padd(pmul(u[0], u[0]), pmul(u[1], u[1])), [F(1)]
        else:
            cr = psub(pmul(w[0], d[1]), pmul(w[1], d[0])); dist2_num, den = pmul(cr, cr), L   # dist^2 = cross^2 / L
        margin = psub(dist2_num, pmul(Rm2, den))          # >= 0  <=>  distance >= R m   (den > 0)
        fam.need(margin, f"disc: clearance from edge {i}")
        if lead_sign(margin) < 0: disc_ok = False
    print(f"2. disc of radius {float(R)}*m about ({float(cx0)}*m + {float(cx1)}, {float(cy0)}*m + {float(cy1)}) clear of every edge for all large m: {disc_ok}")

    # ---------- 3. squares ----------
    def row(N, j):
        nx, ny = N
        if j == 0: return [nx, ny, [], []]
        if j == 1: return [nx, ny, nx, ny]
        if j == 2: return [nx, ny, padd(nx, ny), psub(ny, nx)]
        return [nx, ny, ny, pneg(nx)]
    samples = [F(1000003 + 7919 * k) for k in range(12)]   # 12 points > degree of any minor (<= 6)
    eventual, families, n_quads, n_singular = [], [], 0, 0
    for e0 in range(n):
        for e1, e2, e3 in itertools.product(range(n), repeat=3):
            if min(e1, e2, e3) < e0: continue
            n_quads += 1
            es = (e0, e1, e2, e3)
            A = [row(E[e][3], j) for j, e in enumerate(es)]
            b = [E[e][4] for e in es]
            D = det(A)
            if D:
                fam.need(D, f"det {es}")
                # Cramer numerators: X_k = det(A with column k replaced by b); x_k = X_k / D
                X = [det([r[:k] + [b[i]] + r[k+1:] for i, r in enumerate(A)]) for k in range(4)]
                px, py, va, vb = X
                # corners times D
                P = [(px, py), (padd(px, va), padd(py, vb)), (padd(px, psub(va, vb)), padd(py, padd(vb, va))), (psub(px, vb), padd(py, va))]
                ok = True
                for j, e in enumerate(es):
                    a_, b_, d_, N_, c_, L_ = E[e]
                    T = padd(pmul(psub(P[j][0], pmul(D, a_[0])), d_[0]), pmul(psub(P[j][1], pmul(D, a_[1])), d_[1]))   # tau = T / (D L)
                    lo, hi = pmul(T, D), pmul(psub(pmul(D, L_), T), D)
                    fam.need(lo, f"corner {j} of {es} low"); fam.need(hi, f"corner {j} of {es} high")
                    if lead_sign(lo) < 0 or lead_sign(hi) < 0: ok = False
                fam.need(va, f"v {es}"); fam.need(vb, f"v {es}")
                if ok and (va or vb):
                    side2_num, side2_den = padd(pmul(va, va), pmul(vb, vb)), pmul(D, D)
                    eventual.append((es, side2_num, side2_den, P, D))
                continue
            # D identically zero: generic ranks over Q(m), by evaluation at 12 points
            n_singular += 1
            rA = rAb = rF = 0; witness = None
            for m in samples:
                An = [[pval(x, m) for x in r] for r in A]; bn = [pval(x, m) for x in b]
                aug = [r + [v] for r, v in zip(An, bn)]
                forced = aug + [[F(0), F(0), F(1), F(0), F(0)], [F(0), F(0), F(0), F(1), F(0)]]
                rA, rAb, rF = max(rA, nrank(An)), max(rAb, nrank(aug)), max(rF, nrank(forced))
            if rAb > rA:
                # inconsistent wherever some rAb-minor of [A|b] is non-zero: find one and bound its roots
                Ab = [r + [v] for r, v in zip(A, b)]
                found = False
                for rows_ in itertools.combinations(range(4), rAb):
                    for cols_ in itertools.combinations(range(5), rAb):
                        mnr = det([[Ab[i][j] for j in cols_] for i in rows_])
                        if mnr: fam.need(mnr, f"inconsistent {es}"); found = True; break
                    if found: break
                assert found
                continue
            # consistent for generic m: a family of solutions
            Ab = [r + [v] for r, v in zip(A, b)]
            if rAb > 0:
                done = False
                for rows_ in itertools.combinations(range(4), rAb):
                    for cols_ in itertools.combinations(range(5), rAb):
                        mnr = det([[Ab[i][j] for j in cols_] for i in rows_])
                        if mnr: fam.need(mnr, f"family rank {es}"); done = True; break
                    if done: break
            if rF != rAb:
                families.append(es)      # v is not forced to 0: a genuine family may exist
    print(f"3. edge quadruples examined: {n_quads}; identically singular: {n_singular}; of those, possible genuine families: {len(families)}")
    if families: print("   FAMILIES NOT EXCLUDED:", families[:10])

    # distinct squares among the eventual solutions: compare corner sets at one large sample
    m_big = F(10) ** 9 + 7
    seen, squares = {}, []
    for es, s2n, s2d, P, D in eventual:
        Dv = pval(D, m_big)
        key = frozenset((pval(Pj[0], m_big) / Dv, pval(Pj[1], m_big) / Dv) for Pj in P)
        if key not in seen:
            seen[key] = True; squares.append((es, s2n, s2d))
    print(f"   inscribed squares for every real m > M0: {len(squares)}")
    side_bound = F(0)
    for es, s2n, s2d in sorted(squares, key=lambda q: -float(pval(q[1], m_big) / pval(q[2], m_big))):
        dn, dd = len(s2n) - 1, len(s2d) - 1
        limit = (s2n[-1] / s2d[-1]) if dn == dd else (F(0) if dn < dd else None)
        print(f"     edges {es}: side^2 = [deg {dn}] / [deg {dd}]  ->  limit side = {'UNBOUNDED' if limit is None else f'{math.sqrt(limit):.6f}'}   side at m=1e9: {math.sqrt(pval(s2n, m_big) / pval(s2d, m_big)):.6f}")
        if limit is None: side_bound = None
        elif side_bound is not None: side_bound = max(side_bound, limit)
    # rigorous uniform bound: side^2 <= C for all m > M1, with C slightly above the largest limit
    if side_bound is not None and squares:
        C = F(args[args.index("--side") + 1]) ** 2 if "--side" in args else side_bound * F(101, 100)
        for es, s2n, s2d in squares:
            gap = psub(pmul([C], s2d), s2n)
            assert lead_sign(gap) > 0
            fam.need(gap, f"side bound {es}")
        M0 = fam.threshold(start)
        print(f"   every inscribed square has side <= {math.sqrt(C):.6f} for all real m > M0")
        print(f"   polynomials whose sign must not change: {len(fam.polys)}")
        print(f"\nTHRESHOLD  M0 = {float(M0):.6g}   (no polynomial has a real root beyond it; last one: {fam.worst})")
        print(f"CONCLUSION for every real m > M0: the polygon is simple, contains a disc of radius {float(R)}*m,")
        print(f"and its largest inscribed square has side <= {math.sqrt(C):.4f}.  So  side / inradius <= {math.sqrt(C)/float(R):.6f} / m  ->  0.")
    ok = simple and not degenerate and disc_ok and not families and side_bound is not None
    print("ALL CHECKS PASSED" if ok else "NOT CERTIFIED")
    return ok

if __name__ == "__main__":
    sys.exit(0 if main() else 1)

# -*- coding: utf-8 -*-
r"""Venn diagram: two or three sets, with the region contents labelled.

The reason this is parametric rather than a fixed picture: almost every Venn
question is *about a region*.  "How many students are in A but not B" is read
off the ``A`` region; "at least one of the three" is the union of seven
regions.  So the region labels are inputs, and each one is placed at the
region's own centroid -- computed from the circle geometry, not eyeballed.

Two details that make the difference between readable and wrong:

* The **two-circle intersection lens** has its centroid on the line joining the
  centres, at a distance that comes from the lens area -- not at the midpoint,
  which sits too far inside one circle and reads as belonging to it.
* With three circles, the **triple region** is the small curved triangle in the
  middle.  Its centroid is the average of the three pairwise intersection
  points, which is where a reader looks for it.
"""
import math

import numpy as np

from .. import env, layout
from . import _helpers as H

_PALETTE = ["#1565c0", "#c62828", "#2e7d32"]


def _two_regions(r):
    """Region centroids for two overlapping circles of radius ``r``.

    Centres at ``(-r/2, 0)`` and ``(r/2, 0)``: the separation equals the
    radius, which is the widest overlap that still leaves two clearly separate
    crescents.  A larger separation makes the lens a sliver no label fits in.
    """
    c1 = np.array([-0.5 * r, 0.0])
    c2 = np.array([0.5 * r, 0.0])
    # Lens centroid along the centre line.  For equal circles the lens is
    # symmetric about x = 0, so the midpoint is exact here -- and the two
    # crescents are the mirror images of each other about the same point.
    return {
        "A": c1 + np.array([-0.28 * r, 0.0]),
        "AB": np.array([0.0, 0.0]),
        "B": c2 + np.array([0.28 * r, 0.0]),
        "U": np.array([0.0, -1.42 * r]),
    }


def _three_regions(r):
    """Region centroids for three circles arranged on an equilateral triangle."""
    d = 1.02 * r                       # centre distance
    angs = (90.0, 210.0, 330.0)
    centres = [np.array([d * math.cos(math.radians(a)),
                         d * math.sin(math.radians(a))]) for a in angs]
    A, B, C = centres
    out = {
        "A": A + (A - np.mean(centres, axis=0)) * 0.30,
        "B": B + (B - np.mean(centres, axis=0)) * 0.30,
        "C": C + (C - np.mean(centres, axis=0)) * 0.30,
        "AB": 0.5 * (A + B),
        "AC": 0.5 * (A + C),
        "BC": 0.5 * (B + C),
        "ABC": np.mean(centres, axis=0),
        "U": np.array([0.0, -(d + 1.16 * r)]),
    }
    # Push the pairwise labels outward from the centre so they sit in the lens
    # proper rather than on the boundary of the triple region.
    centre = np.mean(centres, axis=0)
    for key in ("AB", "AC", "BC"):
        p = out[key]
        v = p - centre
        n = float(np.linalg.norm(v))
        if n > 1e-9:
            out[key] = p + v / n * 0.26 * r
    return out


def venn(sets=("A", "B"), regions=None, shade=(), r=1.0,
         out_path="math_venn.png"):
    r"""Two or three sets with the contents of each region written in place.

    ``sets`` names the circles (2 or 3).  ``regions`` maps a region key to the
    text drawn in it.  Keys: for two sets ``A``, ``AB``, ``B``, ``U``; for
    three sets ``A``, ``B``, ``C``, ``AB``, ``AC``, ``BC``, ``ABC``, ``U``
    (``U`` is the universe, outside every circle).  ``shade`` lists keys to
    fill.
    """
    plt = env.pyplot()
    names = [str(s) for s in (sets or ())]
    if len(names) not in (2, 3):
        raise ValueError("venn draws two or three sets, got %d" % len(names))
    r = float(r)
    if r <= 0:
        raise ValueError("r must be positive")

    regions = dict(regions or {})
    valid = ({"A", "AB", "B", "U"} if len(names) == 2
             else {"A", "B", "C", "AB", "AC", "BC", "ABC", "U"})
    unknown = set(regions) - valid
    if unknown:
        raise ValueError("unknown region key(s) %s for %d sets (valid: %s)"
                         % (", ".join(sorted(unknown)), len(names),
                            ", ".join(sorted(valid))))
    shade = {str(s) for s in (shade or ())}
    bad_shade = shade - valid
    if bad_shade:
        raise ValueError("cannot shade unknown region(s): %s"
                         % ", ".join(sorted(bad_shade)))

    patches = env.patches()
    fig, ax = plt.subplots(figsize=(4.4, 4.0) if len(names) == 2 else (4.6, 4.3),
                           dpi=300)
    ax.set_aspect("equal")

    if len(names) == 2:
        centres = [np.array([-0.5 * r, 0.0]), np.array([0.5 * r, 0.0])]
        spots = _two_regions(r)
        x_lo, x_hi = -1.75 * r, 1.75 * r
        y_lo, y_hi = -1.75 * r, 1.35 * r
    else:
        d = 1.02 * r
        angs = (90.0, 210.0, 330.0)
        centres = [np.array([d * math.cos(math.radians(a)),
                             d * math.sin(math.radians(a))]) for a in angs]
        spots = _three_regions(r)
        span = d + r
        x_lo, x_hi = -span - 0.35 * r, span + 0.35 * r
        y_lo, y_hi = -span - 1.30 * r, span + 0.30 * r

    # Filled regions first, so the circles' outlines stay crisp on top.
    for i, c in enumerate(centres):
        ax.add_patch(patches.Circle(c, r, facecolor="none",
                                    edgecolor=_PALETTE[i], lw=1.9, zorder=3))
    if shade:
        # Shading must mark *the region*, not the circles it belongs to: filling
        # circle A for region "AB" would darken the A-only crescent too, which
        # is exactly the wrong part of the figure.  Each key becomes a boolean
        # mask over the plane (inside every circle it names, outside the rest),
        # and `contourf` turns that mask into a filled boundary.  A patch with a
        # clip path can only subtract one circle; three sets need the mask.
        n = 620
        gx = np.linspace(x_lo, x_hi, n)
        gy = np.linspace(y_lo, y_hi, n)
        gxx, gyy = np.meshgrid(gx, gy)
        for key in sorted(shade):
            inside = None
            for i, c in enumerate(centres):
                disc = (gxx - c[0]) ** 2 + (gyy - c[1]) ** 2 <= r * r
                inside = disc if inside is None else (inside & disc)
            if inside is None or not inside.any():
                continue
            colour = _PALETTE[0] if len(names) == 2 else "#37474f"
            ax.contourf(gxx, gyy, inside.astype(float), levels=[0.5, 1.5],
                        colors=[colour], alpha=0.22, zorder=2)

    painted = []
    # Set names sit outside each circle, on the ray away from the centre.
    for i, c in enumerate(centres):
        away = c - np.mean(centres, axis=0)
        n = float(np.linalg.norm(away)) or 1.0
        p = c + away / n * (r * 1.10)
        ax.text(p[0], p[1], "$%s$" % names[i], fontsize=12.5,
                color=_PALETTE[i], ha="center", va="center")
        painted.append(names[i])

    for key, text in regions.items():
        p = spots[key]
        ax.text(p[0], p[1], str(text), fontsize=10.5, ha="center",
                va="center", zorder=8)
        painted.append(str(text))

    if "U" in spots and "U" not in regions:
        # Name the universe box only when the caller did not fill it.
        ax.text(spots["U"][0], spots["U"][1], "$U$", fontsize=12,
                ha="center", va="center")
        painted.append("U")
    elif "U" in regions:
        painted.append("U")

    ax.set_xlim(x_lo, x_hi)
    ax.set_ylim(y_lo, y_hi)
    ax.axis("off")
    report = layout.finish(fig, ax, out_path)

    return {"sets": names, "regions": regions, "shaded": sorted(shade),
            "marks": set(painted), "layout": report}

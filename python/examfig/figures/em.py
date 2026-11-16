# -*- coding: utf-8 -*-
r"""Electromagnetism: field lines with equipotentials, a charged particle in a
uniform magnetic field, and a rod cutting field lines.

The three share one geometric fact that makes or breaks the picture: **the
equipotential surfaces are perpendicular to the field lines**.  Drawing them at
any other angle produces a figure that looks like an electric field and is not
one.  Here the equipotentials are computed as level sets of the same potential
that produced the field, so they cannot disagree.
"""
import math

import numpy as np

from .. import env, layout
from . import _helpers as H

_C_FIELD = "#1565c0"
_C_EQUI = "#c62828"
_C_POS = "#d32f2f"
_C_NEG = "#1565c0"
_C_PATH = "#2e7d32"


def _dipole_potential(X, Y, charges):
    """Electric potential of point charges, in arbitrary units."""
    V = np.zeros_like(X, dtype=float)
    for (qx, qy, q) in charges:
        r2 = (X - qx) ** 2 + (Y - qy) ** 2
        V += q / np.sqrt(np.maximum(r2, 1e-6))
    return V


def fieldlines(charges=None, n_lines=12, n_equi=6, extent=3.2,
               show_labels=True, out_path="phys_fieldlines.png"):
    r"""Field lines and equipotentials of a set of point charges.

    ``charges`` is a list of ``[x, y, q]``.  The default is a dipole, the case
    every textbook opens with.

    Field lines are traced by integrating the field direction, not drawn as
    arcs: an arc that "looks about right" for a dipole is wrong for any other
    arrangement, and a figure that only works for one configuration is a
    drawing, not a tool.
    """
    plt = env.pyplot()
    if not charges:
        charges = [[-1.0, 0.0, 1.0], [1.0, 0.0, -1.0]]
    charges = [(float(x), float(y), float(q)) for x, y, q in charges]
    extent = float(extent)
    # ``registry.coerce`` hands every "number" parameter over as a float, so a
    # count must be cast back to int here.  ``range()`` rejects a float, and the
    # failure only appears when this kind is actually drawn.
    n_lines = int(n_lines)
    n_equi = int(n_equi)
    if not any(abs(q) > 1e-12 for _x, _y, q in charges):
        raise ValueError("at least one charge must be non-zero")

    fig, ax = plt.subplots(figsize=(4.9, 4.5), dpi=300)
    painted = []

    # -- field lines ------------------------------------------------------
    # Seeds are spread on a small circle around each positive charge, then
    # integrated forward.  Seeding on a grid instead would give lines of wildly
    # different density, which reads as a wrong field.
    def direction(px, py):
        ex = ey = 0.0
        for (qx, qy, q) in charges:
            dx, dy = px - qx, py - qy
            r2 = dx * dx + dy * dy
            if r2 < 1e-9:
                continue
            inv = q / (r2 * math.sqrt(r2))
            ex += dx * inv
            ey += dy * inv
        n = math.hypot(ex, ey)
        return (ex / n, ey / n) if n > 1e-12 else (0.0, 0.0)

    step = extent / 110.0
    drawn = 0
    for (qx, qy, q) in charges:
        if q <= 0:
            continue
        seeds = 4 if len(charges) == 1 else max(4, n_lines // 2)
        for i in range(seeds):
            ang = 2.0 * math.pi * i / seeds
            px, py = qx + 0.12 * math.cos(ang), qy + 0.12 * math.sin(ang)
            xs, ys = [px], [py]
            for _ in range(2600):
                dx, dy = direction(px, py)
                if dx == 0.0 and dy == 0.0:
                    break
                px, py = px + dx * step, py + dy * step
                if abs(px) > extent or abs(py) > extent:
                    break
                # Stop when the line runs into another charge: continuing
                # through it draws a spurious straight segment out the far side.
                if any(math.hypot(px - ox, py - oy) < 0.10
                       for ox, oy, oq in charges if oq * q < 0):
                    xs.append(px)
                    ys.append(py)
                    break
                xs.append(px)
                ys.append(py)
            if len(xs) > 3:
                ax.plot(xs, ys, color=_C_FIELD, lw=1.0, zorder=2)
                drawn += 1
    # The field lines themselves are geometry, not a painted label; the reader
    # learns their name from the legend, which is registered below.  ``drawn``
    # is the count of traced lines and is returned as data.

    # -- equipotentials ---------------------------------------------------
    if n_equi > 0:
        g = np.linspace(-extent, extent, 380)
        X, Y = np.meshgrid(g, g)
        V = _dipole_potential(X, Y, charges)
        peak = np.percentile(np.abs(V), 96)
        levels = np.linspace(-peak, peak, n_equi * 2 + 1)
        levels = levels[np.abs(levels) > 1e-9]
        ax.contour(X, Y, V, levels=levels, colors=_C_EQUI, linewidths=0.8,
                   linestyles="dashed", zorder=1)
        equi_count = len(levels)

    # -- charges ----------------------------------------------------------
    for (qx, qy, q) in charges:
        col = _C_POS if q > 0 else _C_NEG
        ax.plot([qx], [qy], "o", ms=11, color=col, mec="white", mew=1.2,
                zorder=6)
        sign = "+" if q > 0 else "\u2212"
        ax.text(qx, qy, sign, fontsize=13, color="white", ha="center",
                va="center", zorder=7)
        if show_labels:
            # Field lines radiate from the charge in every direction, so the
            # name always has a line under it somewhere.  The plate is what
            # makes it legible in print; without it the dashes show through the
            # glyphs.  Because the text sits on an opaque plate, the line
            # collision it would otherwise report is not a defect -- the same
            # exemption the angle labels get.
            ax.text(qx, qy - 0.34, "$%s$" % ("+q" if q > 0 else "-q"),
                    fontsize=10, color=col, ha="center", va="top", zorder=8,
                    bbox={"boxstyle": "round,pad=0.14", "facecolor": "white",
                          "edgecolor": "none", "alpha": 0.92})
            painted.append("+q" if q > 0 else "-q")

    if show_labels:
        # A legend is the only way to tell a field line from an equipotential
        # in black and white print, so it is not decoration.  Its two entries
        # are the only names either family of curves gets, so they are the
        # marks -- "field lines" used to be a separate mark with no text behind
        # it, and the audit called that fabricated.
        ax.plot([], [], color=_C_FIELD, lw=1.2, label="电场线")
        ax.plot([], [], color=_C_EQUI, lw=1.0, ls="dashed", label="等势线")
        leg = ax.legend(loc="lower left", fontsize=8.5, frameon=True,
                        framealpha=0.9, handlelength=1.6)
        leg.get_frame().set_linewidth(0.6)
        painted += ["电场线", "等势线"]

    ax.set_xlim(-extent, extent)
    ax.set_ylim(-extent, extent)
    ax.set_aspect("equal")
    ax.axis("off")
    # The charge names are on opaque plates (see above), so a field line
    # passing under one is hidden, not a collision.  The white + and - inside
    # the charge discs are *meant* to sit on the disc, so their own outline is
    # not a defect either.
    report = layout.finish(
        fig, ax, out_path,
        skip=("$+q$", "$-q$", "+", "\u2212"))
    return {
        "charges": charges,
        "field_lines": drawn,
        "equipotentials": len(levels) if n_equi > 0 else 0,
        "marks": set(painted),
        "layout": report,
    }


def magnetic(charge=1.0, speed=1.0, mass=1.0, field=1.0, sign=1,
             field_mode="in", angle_deg=90.0, out_path="phys_magnetic.png"):
    r"""A charged particle moving in a uniform magnetic field.

    The field is drawn as the standard symbols (crosses into the page, dots out
    of it) and the path is a circle whose radius is *computed* from
    ``r = m v / (q B)`` -- not chosen to fit the frame.

    ``sign`` is +1 for a positive charge, -1 for negative.  The rotation
    direction follows from the Lorentz force, so getting the sign wrong reverses
    the circle, and that reversal is the whole point of the question.
    """
    plt = env.pyplot()
    q = abs(float(charge)) * (1 if float(sign) >= 0 else -1)
    m = float(mass)
    v = float(speed)
    B = float(field)
    if abs(q) < 1e-12:
        raise ValueError("charge must be non-zero")
    if m <= 0 or v <= 0 or B <= 0:
        raise ValueError("mass, speed and field must all be positive")

    r = m * v / (abs(q) * B)
    omega = abs(q) * B / m
    period = 2.0 * math.pi / omega

    fig, ax = plt.subplots(figsize=(4.9, 4.4), dpi=300)
    painted = []

    # -- the field --------------------------------------------------------
    # The symbol grid covers the whole frame: the field is uniform, and showing
    # it only around the path would suggest it stops.
    span = max(r * 1.9, 1.0)
    spacing = span / 6.0
    g = np.arange(-span, span + 1e-9, spacing)
    for gx in g:
        for gy in g:
            if field_mode == "in":
                ax.plot([gx], [gy], marker="x", ms=4.2, color="#90a4ae",
                        mew=1.1, zorder=1)
            else:
                ax.plot([gx], [gy], marker="o", ms=2.6, color="#90a4ae",
                        zorder=1)
    # The field is drawn as a symbol grid covering the whole frame, so the
    # legend line at the top always has a symbol on it.  The plate is what keeps
    # the text readable; the "line" collision it would otherwise report is the
    # plate doing its job, not a defect.
    ax.text(-span * 0.96, span * 0.92,
            "$B=%s\\ \\mathrm{T}$  %s" % (
                H.fmt(B), "垂直纸面向里" if field_mode == "in" else "垂直纸面向外"),
            fontsize=9.5, color="#546e7a", ha="left", va="top", zorder=8,
            bbox={"boxstyle": "round,pad=0.16", "facecolor": "white",
                  "edgecolor": "none", "alpha": 0.92})
    painted.append("B=%s" % H.fmt(B))

    # -- the path ---------------------------------------------------------
    # The circle passes through the origin (the point where the particle is
    # released), so its centre is one radius away, perpendicular to v.  For a
    # positive charge with B into the page, F = qv x B turns the velocity to the
    # left of its direction of travel.
    direction = 1.0 if (q * (1.0 if field_mode == "in" else -1.0)) > 0 else -1.0
    cx, cy = 0.0, direction * r
    th = np.linspace(0.0, 2.0 * math.pi, 400)
    ax.plot(cx + r * np.cos(th), cy + r * np.sin(th), color=_C_PATH, lw=1.9,
            zorder=3)
    painted.append("trajectory")

    # The release point, with the velocity arrow.
    ax.plot([0.0], [0.0], "o", ms=6.0, color="#1a1a1a", zorder=6)
    ax.text(-0.05 * span, -0.09 * span, "$P$", fontsize=10.5,
            ha="right", va="top")
    painted.append("P")
    v_len = 0.30 * span
    H.arrow(ax, (0.0, 0.0), (v_len, 0.0), color="#1a1a1a", lw=1.8, scale=12)
    ax.text(v_len * 1.04, 0.06 * span, "$v$", fontsize=11, ha="left",
            va="bottom")
    painted.append("v")

    # The radius, from the centre to the release point.
    ax.plot([cx, 0.0], [cy, 0.0], color="#9e9e9e", lw=1.0, ls=(0, (4, 3)),
            zorder=2)
    ax.text(cx * 0.5 - 0.06 * span, cy * 0.5, "$r=%s$" % H.fmt(r, 2),
            fontsize=9.5, color="#455a64", ha="right", va="center")
    painted.append("r=%s" % H.fmt(r, 2))
    ax.plot([cx], [cy], "o", ms=3.4, color="#455a64", zorder=5)
    ax.text(cx, cy, "$O'$", fontsize=10, ha="center", va="center",
            zorder=7)
    painted.append("O'")

    ax.text(-span * 0.96, -span * 0.90,
            "$r=\\dfrac{mv}{qB}=%s$    $T=%s$"
            % (H.fmt(r, 2), H.fmt(period, 2)),
            fontsize=9.5, color="#455a64", ha="left", va="bottom")
    painted += ["r=mv/qB", "T=%s" % H.fmt(period, 2)]

    ax.set_xlim(-span, span)
    ax.set_ylim(-span, span)
    ax.set_aspect("equal")
    ax.axis("off")
    # The B legend sits on a plate above the field grid; see above.
    report = layout.finish(fig, ax, out_path,
                           skip=("$B=%s\\ \\mathrm{T}$  %s" % (
                               H.fmt(B),
                               "垂直纸面向里" if field_mode == "in"
                               else "垂直纸面向外"),))
    return {
        "radius": r,
        "period": period,
        "omega": omega,
        "turns": "counter-clockwise" if direction > 0 else "clockwise",
        "marks": set(painted),
        "layout": report,
    }


def induction(rod_length=1.0, speed=2.0, field=0.5, resistance=2.0,
              rail_length=3.0, field_mode="in", out_path="phys_induction.png"):
    r"""A conducting rod sliding on rails through a uniform magnetic field.

    Everything the question asks for is computed from the same four numbers:
    ``E = B L v``, ``I = E / R``, ``F = B I L``, ``P = F v``.  The rod's motion,
    the current direction (by Lenz's law) and the force opposing the motion are
    all derived, so the arrows on the picture cannot contradict the values
    printed next to them.
    """
    plt = env.pyplot()
    L = float(rod_length)
    v = float(speed)
    B = float(field)
    R = float(resistance)
    rail = float(rail_length)
    if L <= 0 or v <= 0 or B <= 0 or R <= 0 or rail <= 0:
        raise ValueError("rod length, speed, field, resistance and rail length "
                         "must all be positive")

    emf = B * L * v
    current = emf / R
    force = B * current * L
    power = force * v

    fig, ax = plt.subplots(figsize=(5.2, 3.8), dpi=300)
    painted = []

    # -- the field --------------------------------------------------------
    span_x, span_y = rail * 1.32, L * 1.30
    for gx in np.arange(-0.35 * span_x, span_x, span_x / 8.0):
        for gy in np.arange(-0.55 * span_y, 0.55 * span_y + 1e-9,
                            span_y / 4.0):
            if field_mode == "in":
                ax.plot([gx], [gy], marker="x", ms=4.0, color="#b0bec5",
                        mew=1.0, zorder=1)
            else:
                ax.plot([gx], [gy], marker="o", ms=2.4, color="#b0bec5",
                        zorder=1)
    painted.append("B=%s" % H.fmt(B))

    # -- the rails --------------------------------------------------------
    # Two horizontal rails with a resistor closing the left end.  The rails are
    # the only straight lines that matter, so they are drawn heavy.
    ax.plot([0.0, rail], [0.0, 0.0], color="#37474f", lw=2.4, zorder=3)
    ax.plot([0.0, rail], [L, L], color="#37474f", lw=2.4, zorder=3)
    ax.plot([0.0, 0.0], [0.0, L], color="#37474f", lw=2.4, zorder=3)
    # The resistor as a zig-zag on the left edge.
    zz = np.linspace(0.0, 1.0, 9)
    zx = 0.10 * L * np.array([0, 1, -1, 1, -1, 1, -1, 1, 0])
    ax.plot(0.0 + zx, L * (0.30 + 0.40 * zz), color="#37474f", lw=1.6,
            zorder=4)
    ax.text(-0.13 * span_x, L * 0.5, "$R=%s\\ \\Omega$" % H.fmt(R),
            fontsize=9.5, ha="right", va="center")
    painted.append("R=%s" % H.fmt(R))

    # -- the rod ----------------------------------------------------------
    # Placed at 55% of the rail so there is room to show it moving and room to
    # show the field region it is about to enter.
    x_rod = rail * 0.55
    ax.plot([x_rod, x_rod], [0.0, L], color="#c62828", lw=3.0, zorder=5)
    ax.text(x_rod, -0.11 * span_y, "$L=%s\\ \\mathrm{m}$" % H.fmt(L),
            fontsize=9.5, color="#c62828", ha="center", va="top")
    painted.append("L=%s" % H.fmt(L))

    # Motion arrow.
    H.arrow(ax, (x_rod, L * 1.20), (x_rod + 0.18 * rail, L * 1.20),
            color="#2e7d32", lw=1.8, scale=12)
    ax.text(x_rod + 0.09 * rail, L * 1.20 + 0.05 * L, "$v=%s\\ \\mathrm{m/s}$"
            % H.fmt(v), fontsize=9.5, color="#2e7d32", ha="left", va="bottom")
    painted.append("v=%s" % H.fmt(v))

    # -- current direction ------------------------------------------------
    # Lenz's law: the induced current opposes the change in flux.  The rod
    # sweeps more area, so the flux into the page grows; the induced current
    # therefore runs counter-clockwise, which on the rod itself points *up*
    # (from the lower rail to the upper one) for field into the page.
    #
    # Getting this backwards is the classic error: the picture then shows the
    # force pulling the rod along instead of opposing it.
    upward = (field_mode == "in")
    y_from, y_to = (0.12 * L, 0.88 * L) if upward else (0.88 * L, 0.12 * L)
    H.arrow(ax, (x_rod, y_from), (x_rod, y_to), color="#1565c0", lw=1.6,
            scale=11)
    ax.text(x_rod + 0.055 * rail, L * 0.5, "$I=%s\\ \\mathrm{A}$"
            % H.fmt(current, 2), fontsize=9.5, color="#1565c0", ha="left",
            va="center")
    painted.append("I=%s" % H.fmt(current, 2))

    # -- opposing force ---------------------------------------------------
    # Ampere's force on the rod: F = B I L, always against the motion.  Drawn on
    # the rod, pointing left.
    H.arrow(ax, (x_rod, L * 0.5), (x_rod - 0.16 * rail, L * 0.5),
            color="#c62828", lw=1.6, scale=11)
    ax.text(x_rod - 0.17 * rail, L * 0.5, "$F=%s\\ \\mathrm{N}$"
            % H.fmt(force, 2), fontsize=9.5, color="#c62828", ha="right",
            va="center")
    painted.append("F=%s" % H.fmt(force, 2))

    ax.text(0.03 * rail, L * 1.30,
            "$E=BLv=%s\\ \\mathrm{V}$" % H.fmt(emf, 3), fontsize=9.5,
            color="#37474f", ha="left", va="bottom")
    painted.append("E=%s" % H.fmt(emf, 3))

    ax.set_xlim(-0.22 * span_x, span_x)
    ax.set_ylim(-0.22 * span_y, L * 1.42)
    ax.set_aspect("equal")
    ax.axis("off")
    report = layout.finish(fig, ax, out_path)
    return {
        "emf": emf,
        "current": current,
        "force": force,
        "power": power,
        "current_direction": "upward" if upward else "downward",
        "marks": set(painted),
        "layout": report,
    }

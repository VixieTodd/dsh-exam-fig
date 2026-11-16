# -*- coding: utf-8 -*-
r"""Mechanics: force analysis with orthogonal decomposition, projectile motion,
and circular motion with its vertical-loop critical condition.

These three share a drawing problem that no other module has: **the vectors are
the figure**.  A parabola is its curve; a force diagram is a set of arrows whose
lengths, angles and labels must all agree with the numbers in the question.
Every arrow length here is computed from a physical quantity at one common
scale, so "the weight arrow is twice the friction arrow" is visible rather than
asserted.
"""
import math

import numpy as np

from .. import env, layout
from . import _helpers as H

_G = 9.8
_C_FORCE = "#1a1a1a"
_C_COMP = "#c62828"
_C_COMP2 = "#1565c0"
_C_PATH = "#1565c0"
_C_TRACK = "#607d8b"


def _scale_for(magnitudes, room):
    """One pixels-per-newton factor for the whole diagram.

    Drawing each force at its own convenient length is the single most common
    way a force diagram lies: the reader compares arrow lengths, and if they do
    not encode the magnitudes the picture contradicts the numbers.
    """
    peak = max([abs(float(m)) for m in magnitudes] + [1e-9])
    return room / peak


def forces(magnitudes=None, angles=None, weight=0.0, incline_deg=0.0,
           show_decomposition=True, out_path="phys_forces.png"):
    r"""Force diagram on a body, with optional orthogonal decomposition.

    ``magnitudes`` are force magnitudes in newtons, ``angles`` their directions
    in degrees measured from +x (counter-clockwise).  A non-zero ``weight``
    adds the gravitational force straight down; ``incline_deg`` tilts the
    *surface* the body sits on, which is what turns the decomposition into the
    familiar "along the incline / perpendicular to it" pair.

    The decomposition axes rotate with the incline.  A question about a block
    on a slope asks for components along and normal to the slope, not along
    world x and y -- and getting that wrong produces a picture that looks
    perfectly reasonable and answers a different question.
    """
    plt = env.pyplot()
    if not magnitudes:
        # The canonical case: a block on a frictionless incline.
        magnitudes = [6.0, 4.0]
        angles = [0.0, 120.0]
    magnitudes = [abs(float(m)) for m in magnitudes]
    if angles is None or len(angles) != len(magnitudes):
        # Evenly spread, so the arrows never sit on top of each other.  A
        # caller that supplies some angles but not all gets a clear error
        # instead of a silently half-random diagram.
        if angles:
            raise ValueError("angles must have one entry per magnitude "
                             "(got %d magnitudes, %d angles)"
                             % (len(magnitudes), len(angles)))
        angles = [360.0 * i / len(magnitudes) + 30.0
                  for i in range(len(magnitudes))]
    angles = [float(t) for t in angles]
    weight = float(weight)
    tilt = math.radians(float(incline_deg))

    fig, ax = plt.subplots(figsize=(4.9, 4.2), dpi=300)
    painted = []

    # -- the surface ------------------------------------------------------
    if abs(math.degrees(tilt)) > 1e-9:
        # A slope, drawn as a triangle under the body so the angle is visible.
        half = 2.4
        p0 = (-half * math.cos(tilt), -half * math.sin(tilt) - 0.30)
        p1 = (half * math.cos(tilt), half * math.sin(tilt) - 0.30)
        ax.plot([p0[0], p1[0]], [p0[1], p1[1]], color=_C_TRACK, lw=2.0,
                zorder=1)
        ax.plot([p0[0], p0[0]], [p0[1], p0[1] - 0.55], color=_C_TRACK, lw=1.2,
                zorder=1)
        ax.plot([p0[0], p1[0]], [p0[1] - 0.55, p1[1] - 0.55], color=_C_TRACK,
                lw=1.2, ls=(0, (4, 3)), zorder=1)
        # The angle is drawn *at* the base of the slope, with an arc.
        arc = np.linspace(0.0, tilt, 40)
        ax.plot(p0[0] + 0.7 * np.cos(arc), p0[1] + 0.7 * np.sin(arc),
                color="#455a64", lw=1.0, zorder=2)
        ax.text(p0[0] + 0.92 * math.cos(tilt * 0.5),
                p0[1] + 0.92 * math.sin(tilt * 0.5),
                "$%s^\\circ$" % H.fmt(incline_deg, 1), fontsize=9.5,
                color="#455a64", ha="left", va="center")
        painted.append("%s deg" % H.fmt(incline_deg, 1))

    # -- the body ---------------------------------------------------------
    body = plt.Rectangle((-0.26, -0.26), 0.52, 0.52, facecolor="#eceff1",
                         edgecolor="#37474f", lw=1.4, zorder=3)
    ax.add_patch(body)

    # -- arrows -----------------------------------------------------------
    # Everything is scaled by the largest force, so the picture is one drawing
    # at one scale.  The body is 0.52 wide, so the longest arrow is 1.55.
    room = 1.55
    all_mag = list(magnitudes) + ([weight] if weight > 0 else [])
    k = _scale_for(all_mag, room)

    tips = []
    for mag, ang in zip(magnitudes, angles):
        rad = math.radians(ang)
        tip = (k * mag * math.cos(rad), k * mag * math.sin(rad))
        H.arrow(ax, (0.0, 0.0), tip, color=_C_FORCE, lw=1.8, scale=13)
        # The label goes just beyond the tip, along the arrow's own direction:
        # placing it at a fixed offset would put a short arrow's label on top of
        # a long one's shaft.
        off = 0.20
        ax.text(tip[0] + off * math.cos(rad), tip[1] + off * math.sin(rad),
                "$F_{%d}=%s\\ \\mathrm{N}$" % (len(tips) + 1, H.fmt(mag)),
                fontsize=9.5, ha="left" if math.cos(rad) >= 0 else "right",
                va="center")
        painted.append("F_%d=%s" % (len(tips) + 1, H.fmt(mag)))
        tips.append(tip)

    if weight > 0:
        tip = (0.0, -k * weight)
        H.arrow(ax, (0.0, 0.0), tip, color="#37474f", lw=1.8, scale=13)
        ax.text(0.16, tip[1] - 0.16, "$G=%s\\ \\mathrm{N}$" % H.fmt(weight),
                fontsize=9.5, color="#37474f", ha="left", va="top")
        painted.append("G=%s" % H.fmt(weight))
        tips.append(tip)

    # -- decomposition ----------------------------------------------------
    if show_decomposition and magnitudes:
        # Axes: along the surface and normal to it.
        ca, sa = math.cos(tilt), math.sin(tilt)
        u_axis = (ca, sa)                       # along the slope
        n_axis = (-sa, ca)                      # normal to it
        # Decompose the resultant of every force except the ones already
        # aligned.  Decomposing the resultant (not each force separately) is
        # what a student draws, and it keeps the picture to two extra arrows.
        rx = sum(k * m * math.cos(math.radians(a))
                 for m, a in zip(magnitudes, angles))
        ry = sum(k * m * math.sin(math.radians(a))
                 for m, a in zip(magnitudes, angles))
        if weight > 0:
            ry -= k * weight
        comp_u = rx * u_axis[0] + ry * u_axis[1]
        comp_n = rx * n_axis[0] + ry * n_axis[1]

        # The two component arrows are drawn from the origin as a dashed pair,
        # so they read as *parts of* the resultant and never as extra forces.
        #
        # The label is built inside the loop, not in the tuple being iterated:
        # a name that mentions ``comp`` cannot be evaluated before the loop has
        # bound it, and Python reports that as UnboundLocalError rather than as
        # the ordering mistake it is.
        for which, axis, col, sym in (
                ("parallel", u_axis, _C_COMP, "F_{\\parallel}"),
                ("perp", n_axis, _C_COMP2, "F_{\\perp}")):
            comp = comp_u if which == "parallel" else comp_n
            if abs(comp) < 1e-6:
                continue
            s = 1.0 if comp >= 0 else -1.0
            tip = (comp * axis[0], comp * axis[1])
            name = "$%s=%s$" % (sym, H.fmt(abs(comp) / k, 2))
            H.arrow(ax, (0.0, 0.0), tip, color=col, lw=1.4, scale=10,
                    style="-|>")
            # Guide lines from the component tips to the resultant tip close the
            # parallelogram; without them the arrows look like three unrelated
            # forces rather than one force resolved into two.
            H.guide(ax, tip, (rx, ry), color=col, lw=0.9)
            mx, my = tip[0] * 1.06, tip[1] * 1.06
            ax.text(mx, my, name, fontsize=9, color=col,
                    ha="left" if s > 0 else "right", va="bottom")
            painted.append(name.strip("$"))
        # The resultant itself.
        if math.hypot(rx, ry) > 1e-6:
            ax.plot([rx], [ry], "o", ms=3.2, color="#455a64", zorder=6)

    span = 2.35
    ax.set_xlim(-span, span)
    ax.set_ylim(-span, span)
    ax.set_aspect("equal")
    ax.axis("off")
    report = layout.finish(fig, ax, out_path)
    return {
        "magnitudes": magnitudes,
        "angles": angles,
        "weight": weight,
        "incline_deg": float(incline_deg),
        "marks": set(painted),
        "layout": report,
    }


def projectile(speed=10.0, angle_deg=45.0, height=0.0, launch_height=0.0,
               gravity=_G, show_components=True, show_range=True,
               out_path="phys_projectile.png"):
    r"""Projectile trajectory with the launch velocity and its components.

    Handles the two textbook variants with one set of equations: ``angle_deg``
    positive is an oblique throw, ``angle_deg == 0`` a horizontal one (平抛),
    and ``launch_height`` above zero a throw from a height.

    Range, peak and time of flight are *solved*, not drawn: the curve is sampled
    from x(t), y(t) and the marked range/peak come from the same solution, so a
    wrong-looking picture cannot coexist with right-looking numbers.
    """
    plt = env.pyplot()
    v0 = float(speed)
    th = math.radians(float(angle_deg))
    g = float(gravity)
    y0 = float(launch_height)
    if v0 <= 0:
        raise ValueError("speed must be positive, got %g" % v0)
    if g <= 0:
        raise ValueError("gravity must be positive, got %g" % g)
    if height and not y0:
        y0 = float(height)

    vx = v0 * math.cos(th)
    vy = v0 * math.sin(th)

    # Time of flight: the positive root of y0 + vy t - g t^2 / 2 = 0.
    disc = vy * vy + 2.0 * g * y0
    t_flight = (vy + math.sqrt(disc)) / g
    t_peak = max(vy / g, 0.0)
    x_range = vx * t_flight
    y_peak = y0 + vy * t_peak - 0.5 * g * t_peak ** 2

    t = np.linspace(0.0, t_flight, 500)
    xs = vx * t
    ys = y0 + vy * t - 0.5 * g * t * t

    fig, ax = plt.subplots(figsize=(5.2, 3.6), dpi=300)
    painted = []

    # Ground line and launch height.
    x_lo = -0.12 * max(x_range, 1.0)
    x_hi = x_range * 1.18 + 0.2
    ax.plot([x_lo, x_hi], [0.0, 0.0], color="#455a64", lw=1.6, zorder=1)
    if y0 > 0:
        ax.plot([0.0, 0.0], [0.0, y0], color=_C_TRACK, lw=1.2, ls=(0, (4, 3)),
                zorder=1)
        ax.text(0.0, y0 * 0.5, "$h=%s$" % H.fmt(y0, 2), fontsize=9,
                color=_C_TRACK, ha="right", va="center")
        painted.append("h=%s" % H.fmt(y0, 2))

    ax.plot(xs, ys, color=_C_PATH, lw=1.9, zorder=3)
    painted.append("trajectory")

    # Launch velocity and its components.  The arrow length is a fraction of the
    # range, so it stays legible whether the throw is short or long.
    if show_components:
        k = 0.22 * max(x_range, 1.0) / v0
        H.arrow(ax, (0.0, y0), (k * vx, y0 + k * vy), color="#1a1a1a",
                lw=1.8, scale=12)
        ax.text(k * vx * 1.02, y0 + k * vy * 1.02 + 0.06 * y_peak,
                "$v_0=%s$" % H.fmt(v0), fontsize=9.5, ha="left", va="bottom")
        painted.append("v0=%s" % H.fmt(v0))
        if abs(vx) > 1e-9:
            H.guide(ax, (0.0, y0), (k * vx, y0), color=_C_COMP, lw=1.1)
            ax.text(k * vx * 0.5, y0 - 0.055 * max(y_peak, 1.0),
                    "$v_x=%s$" % H.fmt(vx, 2), fontsize=9, color=_C_COMP,
                    ha="center", va="top")
            painted.append("vx=%s" % H.fmt(vx, 2))
        if abs(vy) > 1e-9:
            H.guide(ax, (k * vx, y0), (k * vx, y0 + k * vy), color=_C_COMP2,
                    lw=1.1)
            ax.text(k * vx + 0.02 * max(x_range, 1.0), y0 + k * vy * 0.5,
                    "$v_y=%s$" % H.fmt(vy, 2), fontsize=9, color=_C_COMP2,
                    ha="left", va="center")
            painted.append("vy=%s" % H.fmt(vy, 2))
        # The launch angle, drawn as an arc between the ground and v0.
        if abs(angle_deg) > 0.5 and y0 == 0.0:
            r_arc = 0.30 * k * v0
            arc = np.linspace(0.0, th, 40)
            ax.plot(r_arc * np.cos(arc), r_arc * np.sin(arc), color="#455a64",
                    lw=1.0, zorder=4)
            ax.text(r_arc * 1.12 * math.cos(th * 0.5),
                    r_arc * 1.12 * math.sin(th * 0.5),
                    "$%s^\\circ$" % H.fmt(angle_deg, 1), fontsize=9.5,
                    color="#455a64", ha="left", va="bottom")
            painted.append("%s deg" % H.fmt(angle_deg, 1))

    # Peak: a dashed drop to the axis, because "how high does it go" is read
    # from the height of that line.
    if t_peak > 0 and y_peak > 0:
        H.guide(ax, (vx * t_peak, 0.0), (vx * t_peak, y_peak), color="#9e9e9e")
        H.dot(ax, vx * t_peak, y_peak, color="#455a64", ms=4.2)
        ax.text(vx * t_peak, y_peak + 0.05 * y_peak, "$H=%s$" % H.fmt(y_peak, 2),
                fontsize=9.5, color="#455a64", ha="center", va="bottom")
        painted.append("H=%s" % H.fmt(y_peak, 2))

    if show_range:
        ax.annotate("", xy=(x_range, -0.10 * max(y_peak, 1.0)),
                    xytext=(0.0, -0.10 * max(y_peak, 1.0)),
                    arrowprops=dict(arrowstyle="<|-|>", color="#455a64",
                                    lw=1.1, mutation_scale=9), zorder=4)
        ax.text(x_range * 0.5, -0.19 * max(y_peak, 1.0),
                "$x=%s$" % H.fmt(x_range, 2), fontsize=9.5, color="#455a64",
                ha="center", va="top")
        painted.append("x=%s" % H.fmt(x_range, 2))
        H.dot(ax, x_range, 0.0, color=_C_PATH, ms=4.6)

    y_lo = -0.30 * max(y_peak, 1.0) - 0.2
    y_hi = y_peak * 1.20 + 0.2
    ax.set_xlim(x_lo, x_hi)
    ax.set_ylim(y_lo, y_hi)
    ax.axis("off")
    report = layout.finish(fig, ax, out_path)
    return {
        "vx": vx,
        "vy": vy,
        "t_flight": t_flight,
        "range": x_range,
        "peak_height": y_peak,
        "peak_time": t_peak,
        "marks": set(painted),
        "layout": report,
    }


def circular(radius=2.0, speed=4.0, mass=0.5, angle_deg=35.0,
             show_critical=True, show_forces=True,
             out_path="phys_circular.png"):
    r"""Vertical circular motion: the track, the body, and the critical speed.

    At the top of a vertical loop the normal force can only push, so
    ``m v^2 / r >= m g`` -- the critical speed ``v_c = sqrt(g r)`` is the
    minimum speed that keeps the body on the track.  Below it the body leaves
    the track before reaching the top, which is exactly what the question asks
    the reader to work out, so the figure must show both the speed in use and
    the threshold.
    """
    plt = env.pyplot()
    r = float(radius)
    v = float(speed)
    m = float(mass)
    if r <= 0:
        raise ValueError("radius must be positive, got %g" % r)
    if m <= 0:
        raise ValueError("mass must be positive, got %g" % m)

    v_crit = math.sqrt(_G * r)
    fig, ax = plt.subplots(figsize=(4.6, 4.4), dpi=300)
    painted = []

    th = np.linspace(0.0, 2.0 * math.pi, 400)
    ax.plot(r * np.cos(th), r * np.sin(th), color=_C_TRACK, lw=2.0, zorder=1)
    painted.append("track")

    # Centre and the two extreme points.  The top is where the critical
    # condition lives, so it gets a named point.
    H.dot(ax, 0.0, 0.0, color="#455a64", ms=3.4)
    ax.text(-0.10, -0.12, "$O$", fontsize=10, ha="right", va="top")
    ax.plot([0.0], [r], "o", ms=4.6, color="#1a1a1a", zorder=5)
    ax.text(0.0, r + 0.20, "$A$", fontsize=11, ha="center", va="bottom")
    ax.plot([0.0], [-r], "o", ms=4.6, color="#1a1a1a", zorder=5)
    ax.text(0.0, -r - 0.20, "$B$", fontsize=11, ha="center", va="top")
    painted += ["O", "A", "B"]

    # The body at the angle given (measured from the top, going round).
    phi = math.radians(float(angle_deg))
    bx = r * math.sin(phi)
    by = r * math.cos(phi)
    ax.plot([0.0, bx], [0.0, by], color="#9e9e9e", lw=1.0, ls=(0, (4, 3)),
            zorder=2)
    ax.plot([bx], [by], "o", ms=7.0, color=_C_COMP, zorder=6)
    ax.text(bx * 1.10 + 0.10, by * 1.10, "$P$", fontsize=11,
            color=_C_COMP, ha="left", va="bottom")
    painted.append("P")

    if show_forces:
        # Weight: always straight down, from the body.
        w_len = 0.30 * r
        H.arrow(ax, (bx, by), (bx, by - w_len), color="#37474f", lw=1.6,
                scale=11)
        ax.text(bx + 0.06 * r, by - w_len - 0.04 * r, "$mg$", fontsize=9.5,
                color="#37474f", ha="left", va="top")
        painted.append("mg")
        # Normal force: along the radius, inward.
        n_len = 0.30 * r
        ux, uy = -bx / r, -by / r
        H.arrow(ax, (bx, by), (bx + n_len * ux, by + n_len * uy),
                color=_C_COMP2, lw=1.6, scale=11)
        ax.text(bx + n_len * ux * 1.16, by + n_len * uy * 1.16, "$N$",
                fontsize=9.5, color=_C_COMP2, ha="center", va="center")
        painted.append("N")
        # Centripetal resultant.
        need = m * v * v / r
        ax.text(-0.02 * r, -0.62 * r,
                "$F_n=\\dfrac{mv^2}{r}=%s\\ \\mathrm{N}$" % H.fmt(need, 2),
                fontsize=9.5, color="#455a64", ha="center", va="top")
        painted.append("F_n=%s" % H.fmt(need, 2))

    if show_critical:
        # The critical speed as a labelled statement, placed where the top of
        # the loop has empty space -- outside the circle, above A.
        ax.text(0.0, r * 1.42,
                "$v_c=\\sqrt{gr}=%s\\ \\mathrm{m/s}$" % H.fmt(v_crit, 2),
                fontsize=9.5, color="#c62828", ha="center", va="bottom")
        painted.append("v_c=%s" % H.fmt(v_crit, 2))
        # Whether the body given stays on the track is the answer the question
        # wants; state it, and colour the verdict.
        ok = v >= v_crit
        ax.text(0.0, -r * 1.42,
                "$v=%s\\ \\mathrm{m/s}$  %s" % (H.fmt(v, 2),
                                               "能通过最高点" if ok else "不能到达最高点"),
                fontsize=9.5, color="#2e7d32" if ok else "#c62828",
                ha="center", va="top")
        painted.append("v=%s" % H.fmt(v, 2))
        painted.append("能通过最高点" if ok else "不能到达最高点")

    span = r * 1.72
    ax.set_xlim(-span, span)
    ax.set_ylim(-span, span)
    ax.set_aspect("equal")
    ax.axis("off")
    report = layout.finish(fig, ax, out_path)
    return {
        "radius": r,
        "speed": v,
        "critical_speed": v_crit,
        "passes_top": v >= v_crit,
        "centripetal_force": m * v * v / r,
        "marks": set(painted),
        "layout": report,
    }

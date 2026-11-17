# -*- coding: utf-8 -*-
r"""Optics pictures that a numeric answer can be read off.

Three figures, each with a different invariant:

* ``refraction`` -- Snell's law drawn with the *normal* as the reference, not
  the interface.  ``n1 sin(i) = n2 sin(r)``; when ``n1 > n2`` the critical angle
  ``asin(n2/n1)`` is drawn as a third ray along the interface and labelled, and
  asking for an angle of incidence beyond it raises instead of drawing a ray
  that cannot exist.
* ``doubleslit`` -- the fringe pattern as an intensity curve plus the bright
  bands themselves.  Fringe spacing is ``lambda L / d``, and the number of
  bands is computed from the window, never guessed.
* ``energylevel`` -- a hydrogen-like level ladder with the transition arrows.
  The photon energies are ``13.6 * Z**2 * (1/n_lo**2 - 1/n_hi**2)`` eV and each
  arrow is labelled with the wavelength it corresponds to.

The shared rule: **a physical quantity that the prose quotes must be computed
here and returned**, so a mismatch between figure and text shows up as a
different number, not as a subtly wrong picture.
"""
import math

import numpy as np

from .. import env
from . import _helpers as H

_RAY = "#1565c0"
_CRIT = "#c62828"
_NORMAL = "#9e9e9e"


def refraction(n1=1.0, n2=1.5, incidence_deg=45.0, show_critical=True,
               out_path="phys_refraction.png"):
    r"""Refraction at a plane interface, with the critical angle when it exists.

    ``n1`` is the medium the incident ray comes *from*.  The interface is
    horizontal, so the normal is vertical and every angle is measured from it --
    drawing angles from the interface is the single most common way these
    figures end up wrong.
    """
    plt = env.pyplot()
    n1, n2 = float(n1), float(n2)
    inc = float(incidence_deg)
    if n1 <= 0 or n2 <= 0:
        raise ValueError("refractive indices must be positive")
    if not 0.0 <= inc < 90.0:
        raise ValueError("incidence_deg must be in [0, 90)")

    critical = math.degrees(math.asin(n2 / n1)) if n1 > n2 else None
    if critical is not None and inc > critical + 1e-9:
        raise ValueError(
            "angle of incidence %.2f deg exceeds the critical angle %.2f deg: "
            "total internal reflection, no refracted ray exists"
            % (inc, critical))

    sin_r = n1 * math.sin(math.radians(inc)) / n2
    sin_r = max(-1.0, min(1.0, sin_r))
    refr = math.degrees(math.asin(sin_r))

    fig, ax = plt.subplots(figsize=(5.2, 4.4), dpi=300)
    painted = []

    # Interface: the boundary between the two media, drawn thick.
    ax.plot([-3.4, 3.4], [0.0, 0.0], color="#1a1a1a", lw=2.0, zorder=3)
    ax.text(-3.3, 0.16, "$n_1=%s$" % H.fmt(n1, 3), fontsize=10.5, ha="left",
            va="bottom", color="#37474f")
    ax.text(-3.3, -0.16, "$n_2=%s$" % H.fmt(n2, 3), fontsize=10.5, ha="left",
            va="top", color="#37474f")
    painted += ["n_1=%s" % H.fmt(n1, 3), "n_2=%s" % H.fmt(n2, 3)]

    # The normal at the point of incidence, dashed: every angle is measured
    # from it.
    ax.plot([0.0, 0.0], [-2.6, 2.6], ls=(0, (5, 3)), color=_NORMAL, lw=1.0,
            zorder=2)
    ax.text(0.08, 2.5, r"$\mathrm{normal}$", fontsize=9, color="#757575",
            ha="left", va="top")

    # Incident ray: from the upper left down to the origin.
    Li = 2.8
    xi = -Li * math.sin(math.radians(inc))
    yi = Li * math.cos(math.radians(inc))
    H.arrow(ax, (xi, yi), (0.0, 0.0), color=_RAY, lw=1.8, zorder=5)
    ax.text(xi - 0.10, yi + 0.10, "i", fontsize=10, color=_RAY, ha="right",
            va="bottom")

    # Refracted ray into the lower medium.
    Lr = 2.6
    xr = Lr * math.sin(math.radians(refr))
    yr = -Lr * math.cos(math.radians(refr))
    H.arrow(ax, (0.0, 0.0), (xr, yr), color="#2e7d32", lw=1.8, zorder=5)
    ax.text(xr + 0.10, yr - 0.06, "r", fontsize=10, color="#2e7d32",
            ha="left", va="top")

    # Angle arcs, drawn between the ray and the normal.
    rad = 0.85
    for ang, colour, label, sign in ((inc, _RAY, "$i=%s$" % H.fmt(inc, 3),
                                      -1), (refr, "#2e7d32",
                                            "$r=%s$" % H.fmt(refr, 3), 1)):
        th = np.linspace(0.0, math.radians(ang), 60)
        # Measure from the normal (the +y axis) towards the ray.
        ax.plot(sign * rad * np.sin(th), rad * np.cos(th), color=colour,
                lw=1.1, zorder=4)
        painted.append(label.strip("$"))
    ax.text(-0.55, 1.35, "$i=%s$" % H.fmt(inc, 3), fontsize=9.5, color=_RAY,
            ha="center", va="center")
    ax.text(0.62, -1.30, "$r=%s$" % H.fmt(refr, 3), fontsize=9.5,
            color="#2e7d32", ha="center", va="center")

    # The critical ray: along the interface, only when n1 > n2.
    if critical is not None and show_critical:
        Lc = 3.0
        H.arrow(ax, (0.0, 0.0), (Lc, 0.0), color=_CRIT, lw=1.4, zorder=5)
        ax.text(Lc - 0.05, 0.16, r"$C=%s$" % H.fmt(critical, 3), fontsize=9.5,
                color=_CRIT, ha="right", va="bottom")
        painted.append("C=%s" % H.fmt(critical, 3))
        # And the arc from the normal out to the critical ray.
        th = np.linspace(0.0, math.radians(critical), 60)
        ax.plot(1.6 * np.sin(th), 1.6 * np.cos(th), color=_CRIT, lw=1.0,
                ls=(0, (4, 3)), zorder=4)

    ax.set_xlim(-3.6, 3.6)
    ax.set_ylim(-2.9, 2.9)
    ax.set_aspect("equal")
    ax.axis("off")
    report = H.finish_panels(fig, [ax], out_path)

    return {
        "refracted_deg": refr,
        "critical_deg": critical,
        "total_internal_reflection": critical is not None and inc >= critical,
        "ratio": n1 / n2,
        "marks": set(painted),
        "layout": report,
    }


def doubleslit(wavelength=600.0, slit_separation=0.20, distance=1.0,
               window_mm=20.0, n_fringes=9, out_path="phys_doubleslit.png"):
    r"""Two-slit fringes: the intensity curve and the bright bands.

    All lengths are in SI except ``wavelength`` (nanometres) and ``window_mm``
    (millimetres of screen shown), because that is how the question states them.
    The fringe spacing ``lambda L / d`` is computed and returned in millimetres;
    the bands are then placed by that spacing, so the picture and the number can
    never disagree.
    """
    plt = env.pyplot()
    lam = float(wavelength) * 1e-9
    # ``slit_separation`` is stated in millimetres -- the unit a question uses
    # for a slit spacing -- so it must be converted here.  Treating it as metres
    # makes the fringe spacing a thousand times too small, which draws thousands
    # of bands and hangs the renderer.
    d = float(slit_separation) * 1e-3
    L = float(distance)
    if lam <= 0 or d <= 0 or L <= 0:
        raise ValueError("wavelength, slit separation and distance must be positive")

    spacing = lam * L / d                     # metres
    spacing_mm = spacing * 1e3
    half = float(window_mm) / 2.0             # millimetres
    if half <= 0:
        raise ValueError("window_mm must be positive")

    # x on the screen, in millimetres, centred on the central maximum.
    xs_mm = np.linspace(-half, half, 2000)
    # Phase difference from the path difference d*sin(theta) ~ d*x/L.
    phase = 2.0 * math.pi * d * (xs_mm * 1e-3) / (lam * L)
    intensity = np.cos(phase / 2.0) ** 2

    fig, ax = plt.subplots(figsize=(5.8, 3.4), dpi=300)
    painted = []

    # The bands themselves: bright where the intensity peaks, so the drawing is
    # the same function as the curve below it.
    order = int(math.floor(half / spacing_mm))
    # A window that holds hundreds of fringes is a parameter mistake, not a
    # figure: each band is a filled patch, and the renderer grinds to a halt
    # long before the image is readable.  Refuse it and say what to change.
    if order > 200:
        raise ValueError(
            "%d fringes fit in the %g mm window; widen the fringes (longer "
            "wavelength, larger distance, smaller slit separation) or shrink "
            "window_mm" % (order, float(window_mm)))
    for m in range(-order, order + 1):
        xm = m * spacing_mm
        if abs(xm) > half:
            continue
        w = 0.30 * spacing_mm
        # A band marks the bright fringe, so it belongs above the axis, where the
        # intensity is.  ``axvspan`` spans the whole axes by default, and its
        # edges then run down through the fringe numbers printed under the axis.
        ax.add_patch(plt.Rectangle((xm - w, 0.0), 2.0 * w, 1.0,
                                   facecolor="#ffd54f", alpha=0.55, lw=0,
                                   zorder=1))

    ax.plot(xs_mm, intensity, color="#1a1a1a", lw=1.6, zorder=4)
    ax.set_xlim(-half, half)
    # The fringe numbers and the axis title both live under the axis.
    # The floor has to leave room for both at 300 dpi: text height is
    # fixed in points while this limit is in data units, so a floor that
    # just clears one line pushes the other out of the frame.
    ax.set_ylim(-0.34, 1.30)

    ax.annotate("", xy=(half * 0.98, 0.0), xytext=(-half * 0.98, 0.0),
                arrowprops=dict(arrowstyle="-|>", color="k", lw=1.1), zorder=5)
    ax.annotate("", xy=(-half * 0.98, 1.18), xytext=(-half * 0.98, -0.02),
                arrowprops=dict(arrowstyle="-|>", color="k", lw=1.1), zorder=5)
    ax.text(half * 0.97, -0.20, "$x/\\mathrm{mm}$", fontsize=10, ha="right",
            va="top")
    ax.text(-half * 0.94, 1.16, r"$I$", fontsize=10, ha="left", va="top")
    painted += ["x/mm", "I"]

    # Central maximum, marked and named -- the reference every other band is
    # counted from.
    H.dot(ax, 0.0, 1.0, filled=True, color=_CRIT, ms=4.4)
    ax.text(0.0, 1.06, r"$0$", fontsize=9.5, ha="center", va="bottom")
    painted.append("0")

    # Fringe spacing: centre to first side maximum, with the number.
    if abs(spacing_mm) < half:
        y_bar = 1.10
        H.bracket(ax, (0.0, y_bar), (spacing_mm, y_bar), color="#555", lw=1.0)
        ax.text(spacing_mm / 2.0, y_bar + 0.03,
                r"$\Delta x=%s$" % H.fmt(spacing_mm, 3), fontsize=9.5,
                color="#333", ha="center", va="bottom")
        painted.append("dx=%s" % H.fmt(spacing_mm, 3))

    # A few orders labelled, so "the third bright fringe" can be located.
    shown = 0
    for m in range(1, order + 1):
        xm = m * spacing_mm
        if abs(xm) >= half * 0.98 or shown >= int(n_fringes):
            break
        ax.text(xm, -0.03, "%d" % m, fontsize=8.5, ha="center", va="top",
                color="#616161")
        ax.text(-xm, -0.03, "-%d" % m, fontsize=8.5, ha="center", va="top",
                color="#616161")
        shown += 1

    ax.axis("off")
    # ``skip`` compares the *raw* text artist string, so the mathtext delimiters
    # have to be in it: passing "x/mm" matched nothing and the axis label was
    # reported as sitting on the axis it names.
    report = H.finish_panels(fig, [ax], out_path,
                             skip=("$x/\\mathrm{mm}$", "$I$"))

    return {
        "fringe_spacing_mm": spacing_mm,
        "fringe_spacing_m": spacing,
        "orders_shown": order,
        "central_maximum": True,
        "marks": set(painted),
        "layout": report,
    }


_RYDBERG_EV = 13.605693122994


def energylevel(z=1.0, n_max=4, transitions=((3, 1), (2, 1)), out_path="phys_energylevel.png"):
    r"""A hydrogen-like energy ladder with the labelled transitions.

    ``transitions`` are ``(n_hi, n_lo)`` pairs; each is drawn as a downward
    arrow labelled with its photon energy in eV.  Levels are placed by their
    energy, not evenly spaced, because the whole point of the diagram is that
    the gaps shrink.

    That shrinking is also the layout problem: at ``n_max=6`` the levels above
    n=3 are a fraction of an eV apart while the plot spans more than 13 eV, so a
    fixed label offset and a fixed font put every one of them on a neighbouring
    level line.  Two things follow, and both are computed rather than guessed:
    the figure grows with the number of levels, and each level's labels are
    sized to the gap on the side they are placed.
    """
    plt = env.pyplot()
    Z = float(z)
    n_max = int(n_max)
    if Z <= 0:
        raise ValueError("z must be positive")

    pairs = [(int(a), int(b)) for a, b in transitions][:6]
    # A transition that reaches above the last drawn level would silently
    # vanish; say which one is wrong instead.
    for pair in pairs:
        n_hi, n_lo = pair
        if not (1 <= n_lo < n_hi <= n_max):
            raise ValueError(
                "transition %r does not fit n_max=%d: both levels must satisfy "
                "1 <= n_lo < n_hi <= n_max.  Raise n_max to at least %d, or "
                "pass transitions=[] to draw the bare ladder."
                % (list(pair), n_max, max(n_hi for n_hi, _lo in pairs)))

    energies = {n: -_RYDBERG_EV * Z * Z / (n * n) for n in range(1, n_max + 1)}
    # The lowest level is n=1, not n=n_max: energies are negative and get *more*
    # negative as n falls.  Using energies[n_max] as the bottom put the ground
    # state far outside the viewport and every label on it was clipped.
    e_lo, e_hi = energies[1], 0.0

    # The page height is solved for, not guessed.  At n_max=6 the top two rungs
    # of hydrogen are 0.17 eV apart while the ladder spans 14.8 eV, so a 4-inch
    # page gives that gap about 12 px -- less than a third of one line of type.
    # Growing the page until the tightest gap can hold a line is the only way to
    # label every level without stacking text on text.
    gaps = [energies[n + 1] - energies[n] for n in range(1, n_max)]
    y_pad = 0.6
    y_span = (e_hi + y_pad) - (e_lo - y_pad)
    if gaps:
        line_px = 5.5 * 300.0 / 72.0 * 1.15      # a 5.5 pt line plus clearance
        axes_in = y_span * line_px / min(gaps) / 300.0
        # 12 in, not 9.5: at n_max=6 the top two rungs of hydrogen are 0.17 eV
        # apart against a 14.8 eV span, and a 9.5 in page left that gap 26 px
        # tall -- narrower than one line of type at any readable size.
        fig_h = min(12.0, max(4.0, axes_in / 0.78))
    else:
        fig_h = 4.0
    fig, ax = plt.subplots(figsize=(5.6, fig_h), dpi=300)
    painted = []

    x_lo, x_hi = 0.0, 10.0
    ax.set_xlim(x_lo - 1.4, x_hi + 1.4)
    ax.set_ylim(e_lo - y_pad, e_hi + y_pad)

    # Each level's labels sit *outside* the line's x-range and are centred on the
    # level, so a level line can never cross the label that names it.  What can
    # still go wrong is two neighbouring rungs being closer together than one
    # line of type -- at n_max=6 the top two are 0.17 eV apart while the plot
    # spans 13.6 eV.  Those labels are therefore sized to the gap they sit in,
    # and refitted once more after the viewport is final (see below), because
    # growing the viewport changes the height of a glyph in data units.
    level_labels = []
    for n in range(1, n_max + 1):
        e = energies[n]
        ax.plot([x_lo, x_hi], [e, e], color="#1a1a1a", lw=1.8, zorder=3)
        # Half the label may reach into each neighbouring gap.
        room = min([g for g in (energies[n + 1] - e if n < n_max else None,
                                e - energies[n - 1] if n > 1 else None)
                    if g is not None] or [y_pad])
        t_n = H.offset_text(ax, (x_lo, e), "$n=%d$" % n, dx_pt=-4.0,
                            ha="right", va="center", fontsize=10)
        t_e = H.offset_text(ax, (x_hi, e), "$%s\\ \\mathrm{eV}$" % H.fmt(e, 2),
                            dx_pt=4.0, ha="left", va="center", fontsize=9,
                            color="#455a64")
        level_labels.append((t_n, room, 10.0))
        level_labels.append((t_e, room, 9.0))
        painted += ["n=%d" % n, H.fmt(e, 2)]

    # Ionised limit: n -> infinity has energy 0.
    ax.plot([x_lo, x_hi], [0.0, 0.0], ls=(0, (5, 3)), color="#9e9e9e", lw=1.0,
            zorder=2)
    H.offset_text(ax, (x_hi, 0.0), r"$n=\infty$", dx_pt=4.0, ha="left",
                  va="center", fontsize=9, color="#757575")
    painted.append("n=inf")

    # Transitions, spread left to right so two arrows between the same pair of
    # levels do not land on top of each other.
    # One column per transition, spread evenly across the ladder, and the text
    # alternates sides so two columns can never print into each other: the
    # photon-energy string ("108.85 eV") is about two units wide on this
    # scale, wider than a 1.6-unit column pitch.
    span = (x_hi - x_lo)
    pitch = span / float(max(2, len(pairs)))
    for k, (n_hi, n_lo) in enumerate(pairs):
        x = x_lo + pitch * (k + 0.5)
        e_hi_l, e_lo_l = energies[n_hi], energies[n_lo]
        H.arrow(ax, (x, e_hi_l), (x, e_lo_l), color=_RAY, lw=1.5, zorder=5)
        photon = e_hi_l - e_lo_l
        label = "$%d\\!\\to\\!%d$" % (n_hi, n_lo)
        mid = 0.5 * (e_hi_l + e_lo_l)
        right = (k % 2 == 0)
        dx = 3.0 if right else -3.0
        H.offset_text(ax, (x, mid), label, dx_pt=dx,
                      ha="left" if right else "right", va="center",
                      fontsize=9.5, color=_RAY)
        H.offset_text(ax, (x, mid), "$%s\\ \\mathrm{eV}$" % H.fmt(photon, 2),
                      dx_pt=dx, dy_pt=-7.0,
                      ha="left" if right else "right", va="top",
                      fontsize=8.5, color="#546e7a")
        painted += ["%d->%d" % (n_hi, n_lo), H.fmt(photon, 2)]

    ax.axis("off")
    H.expand_to_fit(fig, ax)
    # Now that the viewport is final, size each level label to its gap.  The
    # constraint is half the distance to each neighbouring rung, so the labels
    # of two close levels cannot grow into each other.
    for artist, room, base in level_labels:
        H.fit_text(ax, fig, artist, max_h=0.92 * room)
    H.shrink_colliding(fig, ax)
    report = H.finish_panels(fig, [ax], out_path, skip=("n=inf",))

    photons = []
    for pair in pairs:
        n_hi, n_lo = int(pair[0]), int(pair[1])
        photons.append({
            "from": n_hi, "to": n_lo,
            "energy_ev": energies[n_hi] - energies[n_lo],
            "wavelength_nm": 1239.841984 / (energies[n_hi] - energies[n_lo]),
        })

    return {
        "energies_ev": {n: e for n, e in energies.items()},
        "ionisation_ev": _RYDBERG_EV * Z * Z,
        "photons": photons,
        "marks": set(painted),
        "layout": report,
    }

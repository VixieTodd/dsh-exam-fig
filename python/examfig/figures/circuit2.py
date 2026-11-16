# -*- coding: utf-8 -*-
r"""Parallel circuits with meters and a sliding rheostat.

The series circuit already exists in :mod:`examfig.figures.circuit`, drawn with
schemdraw.  This module is separate because the *layout* problem is different:
a parallel branch has two nodes that several elements share, so the drawing is
no longer one loop -- and meters must be placed **in series with the branch they
measure** (ammeter) or **across it** (voltmeter).  An ammeter drawn in parallel
with a resistor is not a stylistic slip; it is a wrong circuit, and it is the
single most common error in hand-drawn figures.

schemdraw is used here too, but every wire is placed by coordinates rather than
by chained relative moves: with a branch, a relative chain silently accumulates
error and the two ends stop meeting at the same node.
"""
import schemdraw
import schemdraw.elements as elm

from .. import env, layout


def circuit2(emf=6.0, r1=2.0, r2=3.0, rheostat=4.0, show_ammeter=True,
             show_voltmeter=True, out_path="phys_circuit2.png"):
    r"""Battery feeding ``R1`` in parallel with (``R2`` + rheostat).

    Returns the branch currents and the total current, computed from the
    resistances rather than read off the picture:

    * ``R2`` and the rheostat are in series within their branch
    * that branch is in parallel with ``R1``
    * the ammeter is in the main line (it measures the total current)
    * the voltmeter is across the parallel combination (it measures the
      terminal voltage of that group)

    ``rheostat`` is the resistance of the sliding part *as drawn*.  A question
    that says "the slider is at the midpoint of a 20 ohm rheostat" passes 10.
    """
    env.configure_matplotlib()
    schemdraw.use("matplotlib")

    emf = float(emf)
    r1 = float(r1)
    r2 = float(r2)
    rs = float(rheostat)
    if emf <= 0 or r1 <= 0 or r2 <= 0 or rs < 0:
        raise ValueError("emf, R1 and R2 must be positive; the rheostat may be "
                         "zero but not negative")

    branch2 = r2 + rs
    total = 1.0 / (1.0 / r1 + 1.0 / branch2)
    current_total = emf / total
    current1 = emf / r1
    current2 = emf / branch2

    plt = env.pyplot()
    fig, ax = plt.subplots(figsize=(6.4, 4.0), dpi=300)
    ax.set_frame_on(False)
    ax.axis("off")
    ax.set_aspect("equal")

    # Geometry.  The parallel group occupies the top band; the battery sits in
    # the bottom band; the two meet at the left node.
    XL, XR = 0.0, 6.6
    YT, YB = 3.0, 0.0
    YMID = 1.55                    # the second branch runs here
    XNODE = 4.4                    # where the two branches rejoin

    report = {"collisions": 0, "fixed": 0, "remaining": []}
    # Registered where the mark is painted, not reconstructed afterwards: the
    # meter letters are painted by schemdraw inside the ``with`` block, so that
    # is where they are recorded.
    painted = []

    with schemdraw.Drawing(show=False, canvas=ax) as d:
        d.config(unit=1.0, fontsize=11.5, lw=1.6, font="sans-serif")

        # -- bottom: the battery and the main line ------------------------
        #
        # The ammeter is on the *bottom* run, to the right of the battery, not
        # on the left riser.  Two reasons, and both were real defects:
        #
        # * On the left riser its circle sat exactly where the voltmeter's tap
        #   wire leaves the parallel group, so the tap crossed the meter.
        # * ``MeterA`` paints its "A" inside its own circle, so the letter is
        #   *meant* to sit on the element.  Keeping the whole meter on a run of
        #   its own means the collision audit can be given the letter as an
        #   intentional overlay without that excuse covering anything else.
        # ``MeterA``/``MeterV`` ignore ``.to()``: a ``Source`` keeps its default
        # direction and only the length is taken from the call, so
        # ``.at((2.3, 0)).to((3.2, 0))`` drew an ammeter pointing *up* out of the
        # bottom wire instead of lying along it.  Meters must be oriented with
        # ``.theta()`` and sized with ``.length()``.
        d += elm.Battery().at((XL, YB)).to((1.6, YB))
        d += elm.Line().at((1.6, YB)).to((2.3, YB))
        if show_ammeter:
            d += elm.MeterA().at((2.3, YB)).theta(0).length(0.9)
            painted.append("A")
        else:
            d += elm.Line().at((2.3, YB)).to((3.2, YB))
        d += elm.Line().at((3.2, YB)).to((XR, YB))
        d += elm.Line().at((XR, YB)).to((XR, YT))

        # The left riser is plain copper: the voltmeter taps it at the top of
        # the parallel group, and nothing else may occupy that run.
        d += elm.Line().at((XL, YB)).to((XL, YT))

        # -- top branch: R1 ----------------------------------------------
        d += elm.Resistor().at((XL, YT)).to((2.0, YT))
        d += elm.Line().at((2.0, YT)).to((XNODE, YT))

        # -- middle branch: R2 in series with the rheostat ---------------
        d += elm.Line().at((XL, YT)).to((XL, YMID))
        d += elm.Resistor().at((XL, YMID)).to((1.7, YMID))
        d += elm.Line().at((1.7, YMID)).to((2.1, YMID))
        # A rheostat is drawn as a resistor with an arrow across it: the arrow
        # is what distinguishes it from a fixed resistor, and it is the part a
        # student is expected to recognise.  The element is ``ResistorVar`` --
        # ``VarResistor`` does not exist in schemdraw 0.23 and the AttributeError
        # only fires when this kind is drawn.
        d += elm.ResistorVar().at((2.1, YMID)).to((3.7, YMID))
        d += elm.Line().at((3.7, YMID)).to((XNODE, YMID))

        # -- rejoin ------------------------------------------------------
        d += elm.Line().at((XNODE, YT)).to((XNODE, YMID))

        # -- the voltmeter ------------------------------------------------
        # Drawn *across* the parallel group: from the left node down and right,
        # tapping the bottom line.  It is placed outside the loop so it does
        # not read as a third branch.
        #
        # It is added *before* the single ``d.draw()`` below.  Calling
        # ``d.draw()`` twice redraws every element already in the drawing, so
        # each meter letter was being painted twice, a few pixels apart -- the
        # audit reported "A overlaps A" and the duplicate was real.
        if show_voltmeter:
            # Tapped at the *top* of the left riser, so the tap runs along the
            # top band and down the far left -- clear of every element.
            d += elm.Line().at((XL, YT)).to((XL - 0.95, YT))
            d += elm.Line().at((XL - 0.95, YT)).to((XL - 0.95, 1.95))
            # theta(-90) makes the meter point down, which is the direction the
            # tap runs.  Without it the meter drew upward, over the top wire.
            d += elm.MeterV().at((XL - 0.95, 1.95)).theta(-90).length(0.9)
            painted.append("V")
            d += elm.Line().at((XL - 0.95, 1.05)).to((XL - 0.95, YB))
            d += elm.Line().at((XL - 0.95, YB)).to((XL, YB))

        d.draw(show=False)
        assert d.fig.ax is ax

        # -- element labels -------------------------------------------------
        # Placed at the element midpoint plus a *measured* outward normal, the
        # same rule the series circuit uses.  ``.label(loc="bottom")`` inside
        # schemdraw puts the text on a fixed offset from the wire, and on the
        # middle branch that offset lands the string straight on the copper --
        # the audit reported every one of them as a "line" collision.
        #
        # R2 goes above its branch and the rheostat above it too, but further
        # out: the two sit on the same horizontal run, so they need different
        # heights, and the rheostat's arrow head reaches higher than the
        # zig-zag -- below the element the only free strip is the one the
        # ammeter's circle already occupies.
        labels = [
            ((1.0, YT), (0.0, 1.0), "$R_1=%g\\ \\Omega$" % r1, 0.0),
            ((0.85, YMID), (0.0, 1.0), "$R_2=%g\\ \\Omega$" % r2, 0.0),
            # The arrow crosses the whole element and its head rises above the
            # zig-zag, so the standard clearance is not enough here: an extra
            # 0.30 keeps the string clear of the head.
            ((2.9, YMID), (0.0, 1.0), "$R=%g\\ \\Omega$" % rs, 0.30),
        ]
        ax.set_xlim(XL - 1.9, XR + 0.9)
        ax.set_ylim(YB - 0.9, YT + 0.9)
        fig.canvas.draw()
        renderer = fig.canvas.get_renderer()
        inv = ax.transData.inverted()
        gap, elem_half = 0.20, 0.34
        placed = []
        for (px, py), (nx, ny), s, extra in labels:
            probe = ax.text(px, py, s, fontsize=11.5, ha="center", va="center")
            bb = probe.get_window_extent(renderer=renderer)
            (x0, y0) = inv.transform((bb.x0, bb.y0))
            (x1, y1) = inv.transform((bb.x1, bb.y1))
            half_w, half_h = abs(x1 - x0) / 2, abs(y1 - y0) / 2
            probe.remove()
            # The zig-zag sticks out past the wire centreline, hence elem_half.
            off = (half_w if abs(nx) > 0.5 else half_h) + elem_half + gap + extra
            placed.append(ax.text(px + nx * off, py + ny * off, s,
                                  fontsize=11.5, ha="center", va="center",
                                  zorder=20))
        painted += ["R_1=%g" % r1, "R_2=%g" % r2, "R=%g" % rs]

        # The viewport is grown by measurement, not by a guessed pad: the meter
        # letters and the resistor values are the widest things on the page and
        # a fixed pad clipped them.
        ax.set_xlim(XL - 1.9, XR + 0.9)
        ax.set_ylim(YB - 0.9, YT + 0.9)
        fig.canvas.draw()
        renderer = fig.canvas.get_renderer()
        inv = ax.transData.inverted()
        bx0, by0 = XL - 1.9, YB - 0.9
        bx1, by1 = XR + 0.9, YT + 0.9
        for t in ax.texts:
            bb = t.get_window_extent(renderer=renderer)
            (x0, y0) = inv.transform((bb.x0, bb.y0))
            (x1, y1) = inv.transform((bb.x1, bb.y1))
            bx0, by0 = min(bx0, x0), min(by0, y0)
            bx1, by1 = max(bx1, x1), max(by1, y1)
        ax.set_xlim(bx0 - 0.30, bx1 + 0.30)
        ax.set_ylim(by0 - 0.30, by1 + 0.30)

        fig.canvas.draw()
        collisions = layout.audit(ax)
        report = {
            "collisions": len(collisions),
            "fixed": 0,
            "remaining": [{"kind": c["kind"], "label": c["a"], "with": c["b"]}
                          for c in collisions],
        }
        d.save(out_path, dpi=300)

    return {
        "branch1_current": current1,
        "branch2_current": current2,
        "total_current": current_total,
        "equivalent_resistance": total,
        "terminal_voltage": emf,
        "marks": set(painted),
        "layout": report,
    }

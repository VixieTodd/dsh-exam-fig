# -*- coding: utf-8 -*-
r"""Series circuit: a closed loop drawn with schemdraw, labels outside it.

Why this does not use :func:`examfig.labelplace.place_labels`, even though that
optimiser exists and works:

* The optimiser answers "which of these candidate positions is least
  crowded" for a label that must sit *next to a point* -- an arrow tip, a
  vertex, a root.
* A circuit label is not anchored to a point at all.  "R2 = 4 ohm" describes
  *the whole resistor*, and the textbook rule is that it goes **outside the
  loop**.  Feeding these to the optimiser pushes them inside the loop, which
  is simply wrong.

So the placement is deterministic: element midpoint + outward normal times a
measured offset.  No search, no candidates, but it can never land inside the
loop and it reproduces exactly on every redraw.

The general rule: **ask what the label is anchored to.**  Anchor is a point ->
optimiser.  Anchor is an element -> outward normal.

One ordering rule matters more than the rest: **set the viewport, then measure
the text, then place it.**  Measuring first means the data-to-pixel mapping
changes between measuring and placing, and the label lands on top of the
component.  That was the root cause of several "label prints over the
resistor" iterations.
"""
import schemdraw
import schemdraw.elements as elm

from .. import env, layout


def circuit(emf=6.0, r1=2.0, r2=4.0, out_path="phys_circuit.png",
            W=6.0, H=3.2):
    """A battery and two resistors in series, with the total current.

    Returns ``current``, ``loop_closed`` and the set of labels actually drawn.
    """
    env.configure_matplotlib()
    schemdraw.use("matplotlib")

    TL, TR = (0.0, H), (W, H)
    BR, BL = (W, 0.0), (0.0, 0.0)

    # Assert closure in coordinate space rather than trusting the eye.  An
    # earlier version issued relative moves (right/down/left/up) and left a
    # visible gap wherever the lengths did not add up.
    loop = [TL, TR, BR, BL, TL]
    assert loop[0] == loop[-1], "loop not closed"

    # Supply the Axes ourselves via ``canvas=``.  schemdraw's ``Drawing.draw``
    # branches on ``canvas``: an object exposing ``.plot`` goes to
    # ``_drawmpl(ax=canvas)``, which sets ``userfig = True`` and makes
    # ``getfig()`` leave our viewport alone.  Without this, ``d.save()`` calls
    # ``getfig()``, which overwrites the limits with schemdraw's own content
    # bbox -- every ``set_xlim`` above is silently discarded and wide labels
    # are clipped at the page edge.
    #
    # Note it must be ``canvas=ax``, not ``ax=ax``: unrecognised keywords land
    # in ``dwgparams`` and are swallowed as drawing parameters.
    plt = env.pyplot()
    fig, ax = plt.subplots(figsize=(6.4, 3.4), dpi=300)
    ax.set_frame_on(False)
    ax.set_aspect("equal")
    # A self-made Axes carries ticks and tick labels; schemdraw's own Axes is
    # created with them switched off.  set_frame_on(False) only drops the
    # spine, so the numbers survive into the PNG unless axis("off") is called.
    ax.axis("off")

    # Assigned inside the `with` block; pre-seeded so a report always exists
    # even if schemdraw raises partway through.
    report = {"collisions": 0, "fixed": 0, "remaining": []}

    with schemdraw.Drawing(show=False, canvas=ax) as d:
        d.config(unit=1.0, fontsize=12, lw=1.6, font="sans-serif")

        d += elm.Battery().at(BL).to(TL)
        d += elm.Line().at(TL).to((2.2, H))
        d += elm.Resistor().at((2.2, H)).to((4.0, H))
        d += elm.Line().at((4.0, H)).to(TR)
        d += elm.Line().at(TR).to((W, 2.0))
        d += elm.Resistor().at((W, 2.0)).to((W, 0.9))
        d += elm.Line().at((W, 0.9)).to(BR)
        d += elm.Line().at(BR).to(BL)

        d.draw(show=False)

        # With an injected Axes, d.fig is schemdraw's wrapper around it.
        assert d.fig.ax is ax

        labels = [
            ((3.1, H),  (0.0, 1.0),  "$R_1=%g\\ \\Omega$" % r1),
            ((W, 1.45), (1.0, 0.0),  "$R_2=%g\\ \\Omega$" % r2),
            ((0.0, 1.6), (-1.0, 0.0), "$%g\\ \\mathrm{V}$" % emf),
        ]

        pad = 1.9
        ax.set_xlim(-pad, W + pad)
        ax.set_ylim(-pad * 0.62, H + pad * 0.62)

        fig.canvas.draw()
        renderer = fig.canvas.get_renderer()
        inv = ax.transData.inverted()
        gap, elem_half = 0.22, 0.34

        placed = []
        for (px, py), (nx, ny), s in labels:
            probe = ax.text(px, py, s, fontsize=12, ha="center", va="center")
            bb = probe.get_window_extent(renderer=renderer)
            (x0, y0) = inv.transform((bb.x0, bb.y0))
            (x1, y1) = inv.transform((bb.x1, bb.y1))
            half_w, half_h = abs(x1 - x0) / 2, abs(y1 - y0) / 2
            probe.remove()

            # Resistor zig-zags and battery plates stick out past the wire
            # centreline, hence elem_half on top of the measured text box.
            off = (half_w if abs(nx) > 0.5 else half_h) + elem_half + gap
            placed.append(ax.text(px + nx * off, py + ny * off, s, fontsize=12,
                                  ha="center", va="center", zorder=20))

        # The viewport is sized by the labels, not by a constant.  A fixed
        # pad clipped the right-hand "R2 = 4 ohm" clean off the edge, because
        # that string is much wider than the half-unit of slack assumed.
        fig.canvas.draw()
        bx0, by0 = -pad, -pad * 0.62
        bx1, by1 = W + pad, H + pad * 0.62
        for t in placed:
            bb = t.get_window_extent(renderer=renderer)
            (x0, y0) = inv.transform((bb.x0, bb.y0))
            (x1, y1) = inv.transform((bb.x1, bb.y1))
            bx0, by0 = min(bx0, x0), min(by0, y0)
            bx1, by1 = max(bx1, x1), max(by1, y1)

        grow = 0.45
        ax.set_xlim(bx0 - grow, bx1 + grow)
        ax.set_ylim(by0 - grow * 0.8, by1 + grow * 0.8)

        # Audit before saving, but do not let `layout.finish` save: schemdraw's
        # `d.save` goes through `Figure.save`, which resets the limits to its
        # own content bbox and would throw away the viewport just computed
        # above.  Deterministic placement already keeps the three labels
        # outside the loop, so this is a verdict, not a repair.
        fig.canvas.draw()
        collisions = layout.audit(ax)
        report = {
            "collisions": len(collisions),
            "fixed": 0,
            "remaining": [{"kind": c["kind"], "label": c["a"], "with": c["b"]}
                          for c in collisions],
        }

        d.save(out_path, dpi=300)

    marks = {"R_1=%g" % r1, "R_2=%g" % r2, "%g V" % emf}
    return {"current": emf / (r1 + r2), "loop_closed": True, "marks": marks,
            "layout": report}

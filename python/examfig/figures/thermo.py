# -*- coding: utf-8 -*-
r"""A thermodynamic cycle on the ``p-V`` plane.

``p-V`` diagrams are read in two ways and the figure has to support both: the
*shape* of each process (isotherm, isobar, isochore, adiabat) and the *area* it
encloses, which is the net work.  Both come from one parametrisation here, so a
question quoting "the work done in one cycle" and the picture cannot disagree.

The processes are given as a small list of ``(kind, ...)`` steps, e.g.

    [["isotherm", 2.0], ["isochore", 0.5], ["isotherm", 1.0], ["isochore", 2.0]]

where each step runs from the current state to the next.  ``isotherm`` and
``adiabat`` take the volume to reach; ``isochore`` takes the pressure to reach;
``isobar`` takes the volume to reach.  The cycle is asserted to close.

Net work is computed from the shoelace rule over the sampled path -- the exact
area inside the closed curve -- rather than by summing the per-process formulae,
so an inconsistent step list shows up as a non-closing loop instead of as a
plausible but wrong number.
"""
import math

import numpy as np

from .. import env
from . import _helpers as H

_PROCESS = "#1565c0"
_FILL = "#1565c0"

_GAMMA = 5.0 / 3.0          # monatomic ideal gas


def pv(states=None, processes=None, n_points=400, show_area=True,
       out_path="phys_pv.png"):
    r"""Draw a ``p-V`` cycle and report its enclosed work.

    ``states`` is the starting ``[p, V]``; ``processes`` the step list described
    in the module docstring.  When omitted, a rectangle-shaped Carnot-like cycle
    between ``V=1..3`` and ``p=1..3`` is drawn, which is the shape most questions
    use.
    """
    plt = env.pyplot()
    if processes is None:
        processes = [["isobar", 3.0], ["isochore", 1.0],
                     ["isobar", 1.0], ["isochore", 3.0]]
    if states is None:
        p0, v0 = 3.0, 1.0
    else:
        p0, v0 = float(states[0]), float(states[1])
    if p0 <= 0 or v0 <= 0:
        raise ValueError("the starting pressure and volume must be positive")

    path_p = [p0]
    path_v = [v0]
    p, v = p0, v0
    segments = []

    for step in processes:
        kind = str(step[0]).lower()
        target = float(step[1])
        if target <= 0:
            raise ValueError("a process target must be positive")
        if kind == "isotherm":
            v_new, p_new = target, p * v / target
            ts = np.linspace(0.0, 1.0, n_points)
            vs = v * (v_new / v) ** ts
            ps = p * (v / vs)
        elif kind == "adiabat":
            v_new = target
            p_new = p * (v / v_new) ** _GAMMA
            ts = np.linspace(0.0, 1.0, n_points)
            vs = v * (v_new / v) ** ts
            ps = p * (v / vs) ** _GAMMA
        elif kind == "isochore":
            p_new, v_new = target, v
            ts = np.linspace(0.0, 1.0, n_points)
            vs = np.full_like(ts, v)
            ps = p + (p_new - p) * ts
        elif kind == "isobar":
            v_new, p_new = target, p
            ts = np.linspace(0.0, 1.0, n_points)
            ps = np.full_like(ts, p)
            vs = v + (v_new - v) * ts
        else:
            raise ValueError("unknown process %r (isotherm, adiabat, isochore, "
                             "isobar)" % (kind,))
        segments.append((kind, vs, ps))
        path_v.extend(vs[1:].tolist())
        path_p.extend(ps[1:].tolist())
        p, v = p_new, v_new

    # Closure is the one invariant that makes the area meaningful.
    closed = abs(p - p0) < 1e-6 * max(1.0, p0) and abs(v - v0) < 1e-6 * max(1.0, v0)
    if not closed:
        raise ValueError(
            "the process list does not return to the starting state "
            "(ended at p=%.4g, V=%.4g, started at p=%.4g, V=%.4g)"
            % (p, v, p0, v0))

    vs_all = np.array(path_v)
    ps_all = np.array(path_p)
    # Shoelace: the signed area enclosed by the sampled path.  The sign follows
    # the mathematical convention (positive = counter-clockwise on the V-p
    # plane), which is the *opposite* of the sign of the work: for a clockwise
    # cycle the gas expands at high pressure and is compressed at low pressure,
    # so it does net work, and the shoelace sum is negative.  Getting this
    # backwards turns an engine into a refrigerator.
    shoelace = 0.5 * float(np.sum(vs_all[:-1] * ps_all[1:]
                                 - vs_all[1:] * ps_all[:-1]))
    work = -shoelace
    clockwise = shoelace < 0

    fig, ax = plt.subplots(figsize=(5.0, 4.0), dpi=300)
    painted = []

    v_lo, v_hi = float(vs_all.min()), float(vs_all.max())
    p_lo, p_hi = float(ps_all.min()), float(ps_all.max())
    v_pad = 0.18 * (v_hi - v_lo)
    p_pad = 0.18 * (p_hi - p_lo)
    x_lo, x_hi = max(0.0, v_lo - v_pad), v_hi + v_pad
    y_lo, y_hi = max(0.0, p_lo - p_pad), p_hi + p_pad

    if show_area:
        ax.fill(vs_all, ps_all, color=_FILL, alpha=0.10, lw=0, zorder=1)

    for kind, vs, ps in segments:
        style = (0, (5, 3)) if kind == "isotherm" else "-"
        ax.plot(vs, ps, color=_PROCESS, lw=1.9, ls=style, zorder=4)

    painted.extend(H.frame(ax, (x_lo, x_hi), (y_lo, y_hi), xlabel="$V$",
                           ylabel="$p$", style="corner"))

    # Each corner state, numbered, so "state 2" in the prose can be found.
    corners = [(p0, v0)]
    pp, vv = p0, v0
    for step in processes:
        kind = str(step[0]).lower()
        target = float(step[1])
        if kind == "isotherm":
            vv, pp = target, pp * vv / target
        elif kind == "adiabat":
            pp, vv = pp * (vv / target) ** _GAMMA, target
        elif kind == "isochore":
            pp = target
        else:
            vv = target
        corners.append((pp, vv))

    for i, (pc, vc) in enumerate(corners[:-1]):
        H.dot(ax, vc, pc, filled=True, color="#1a1a1a", ms=4.4)
        ax.text(vc + 0.02 * (x_hi - x_lo), pc + 0.03 * (y_hi - y_lo),
                "$%d$" % (i + 1), fontsize=9.5, ha="left", va="bottom")
        painted.append("%d" % (i + 1))

    # The enclosed work, printed inside the loop where there is always room.
    if abs(work) > 1e-9:
        txt = "$W=%s$" % H.fmt(abs(work), 3)
        ax.text(0.5 * (v_lo + v_hi), 0.5 * (p_lo + p_hi), txt, fontsize=10,
                ha="center", va="center", color="#37474f")
        painted.append("W=%s" % H.fmt(abs(work), 3))

    ax.set_xlim(x_lo, x_hi)
    ax.set_ylim(y_lo, y_hi)
    ax.axis("off")
    report = H.finish_panels(fig, [ax], out_path,
                             skip=("$p$", "$V$", "$O$"))

    return {
        "net_work": work,
        "clockwise": clockwise,
        "states": [{"p": pc, "V": vc} for pc, vc in corners[:-1]],
        "marks": set(painted),
        "layout": report,
    }

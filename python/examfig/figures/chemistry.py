# -*- coding: utf-8 -*-
r"""Chemistry graphs whose axis values are computed, not sketched.

Two figures:

* ``titration`` -- pH against the volume of titrant added.  The curve is *not*
  a hand-drawn sigmoid: at every point the pH comes from solving the charge
  balance of the actual solution, so the steep part lands where the equivalence
  volume is, and the half-equivalence point of a weak acid really is at
  ``pH = pKa``.  A question that asks "read the pH after 10.00 mL" gets the same
  number from the picture as from the calculation.
* ``equilibrium`` -- the forward and reverse rates against time, with a
  perturbation.  Both curves relax towards a *common* rate, because that is what
  equilibrium means; a figure where they cross and keep going is wrong and is
  the usual way this diagram is botched.

Neither function paints a value it did not compute.
"""
import math

import numpy as np

from .. import env
from . import _helpers as H

_KW = 1.0e-14

_C_FWD = "#c62828"
_C_REV = "#1565c0"
_C_PH = "#1e8449"


def _solve_pH(charge_error, lo=-2.0, hi=16.0, tol=1e-10):
    """Root of ``charge_error(pH)`` by bisection on the pH axis.

    Bisecting in pH rather than in ``[H+]`` is deliberate: the interesting range
    spans fourteen decades, and a linear bisection in concentration either
    converges too slowly or steps straight over the equivalence point.
    """
    a, b = lo, hi
    fa, fb = charge_error(a), charge_error(b)
    if fa == 0:
        return a
    if fb == 0:
        return b
    if fa * fb > 0:
        raise ValueError("pH root not bracketed between %g and %g" % (lo, hi))
    for _ in range(200):
        m = 0.5 * (a + b)
        fm = charge_error(m)
        if abs(fm) < tol or (b - a) < tol:
            return m
        if fa * fm <= 0:
            b, fb = m, fm
        else:
            a, fa = m, fm
    return 0.5 * (a + b)


def titration(analyte_conc=0.100, analyte_volume=20.0, titrant_conc=0.100,
              ka=1.8e-5, mode="acid", show_half=True,
              out_path="chem_titration.png"):
    r"""Titration curve: pH against the volume of titrant added.

    ``mode="acid"`` titrates an acid (``ka`` its dissociation constant) with a
    strong base; ``mode="base"`` titrates a base (``kb``, passed as ``ka``) with
    a strong acid.  ``ka >= 1`` is treated as a strong acid.

    Concentrations are mol/L and volumes mL, which is how a question states
    them; the charge balance converts to moles internally.
    """
    plt = env.pyplot()
    Ca = float(analyte_conc)
    Va = float(analyte_volume)
    Cb = float(titrant_conc)
    K = float(ka)
    mode = str(mode).lower()
    if mode not in ("acid", "base"):
        raise ValueError("mode must be 'acid' or 'base'")
    if Ca <= 0 or Va <= 0 or Cb <= 0:
        raise ValueError("concentrations and volume must be positive")
    if K <= 0:
        raise ValueError("ka/kb must be positive")

    v_eq = Ca * Va / Cb                 # mL of titrant at equivalence

    def pH_at(v_added):
        """pH of the mixture after ``v_added`` mL of titrant."""
        n_analyte = Ca * Va / 1000.0
        n_titrant = Cb * v_added / 1000.0
        vol = (Va + v_added) / 1000.0
        c_analyte = n_analyte / vol
        c_titrant = n_titrant / vol

        if mode == "acid":
            def err(ph):
                h = 10.0 ** (-ph)
                oh = _KW / h
                # [A-] from the acid equilibrium, [Na+] from the titrant.
                a_minus = c_analyte * K / (K + h)
                return h + c_titrant - oh - a_minus
        else:
            def err(ph):
                h = 10.0 ** (-ph)
                oh = _KW / h
                # [BH+] from the base equilibrium; the titrant contributes H+,
                # which is the same as removing OH- in the charge balance.
                bh = c_analyte * K / (K + oh)
                return h + bh - oh - c_titrant

        return _solve_pH(err)

    v_max = 2.0 * v_eq
    # Sample densely near the equivalence point: that is where the curve is
    # vertical, and a uniform grid would draw it as a diagonal line.
    v_pts = np.unique(np.concatenate([
        np.linspace(0.0, 0.92 * v_eq, 260),
        np.linspace(0.92 * v_eq, 1.08 * v_eq, 400),
        np.linspace(1.08 * v_eq, v_max, 260),
    ]))
    ph_pts = np.array([pH_at(v) for v in v_pts])

    ph_eq = pH_at(v_eq)
    ph_start = float(ph_pts[0])

    fig, ax = plt.subplots(figsize=(5.2, 3.9), dpi=300)
    painted = []

    ax.plot(v_pts, ph_pts, color=_C_PH, lw=2.0, zorder=4)

    y_lo = max(0.0, min(0.0, float(ph_pts.min())) - 0.6)
    y_hi = min(14.0, float(ph_pts.max()) + 0.6)
    if y_hi - y_lo < 4.0:
        y_lo, y_hi = 0.0, 14.0

    painted.extend(H.frame(ax, (0.0, v_max * 1.02), (y_lo, y_hi),
                           xlabel="$V/\\mathrm{mL}$", ylabel="$\\mathrm{pH}$",
                           style="corner"))

    # Equivalence point: the vertical jump, dotted, plus the point itself.
    H.guide(ax, (v_eq, y_lo), (v_eq, ph_eq), color="#9e9e9e")
    H.dot(ax, v_eq, ph_eq, filled=True, color=_C_PH, ms=4.6)
    ax.text(v_eq + 0.02 * v_max, ph_eq,
            "$(%s\\ \\mathrm{mL},\\ %s)$" % (H.fmt(v_eq, 3), H.fmt(ph_eq, 3)),
            fontsize=9, color="#1b5e20", ha="left", va="center")
    painted += ["Veq=%s" % H.fmt(v_eq, 3), "pHeq=%s" % H.fmt(ph_eq, 3)]

    # Half-equivalence: only meaningful for a weak acid/base, where pH = pKa
    # (or, when titrating a base, pH = 14 - pKb).  The label has to name the
    # constant that is actually true of the figure -- writing pKa on a base
    # titration is a chemistry error, not a typo.
    is_weak = K < 1.0
    p_label = "pKa" if mode == "acid" else "pKb"
    if show_half and is_weak:
        v_half = 0.5 * v_eq
        ph_half = pH_at(v_half)
        H.guide(ax, (v_half, y_lo), (v_half, ph_half), color="#b0b0b0")
        H.dot(ax, v_half, ph_half, filled=False, color="#455a64", ms=4.4)
        ax.text(v_half, y_lo + 0.06 * (y_hi - y_lo),
                "$\\mathrm{%s}=%s$" % (p_label, H.fmt(-math.log10(K), 3)),
                fontsize=9, color="#455a64", ha="center", va="bottom")
        painted.append("%s=%s" % (p_label, H.fmt(-math.log10(K), 3)))

    # The starting pH, which a question usually asks for first.
    ax.text(0.02 * v_max, ph_start, "$%s$" % H.fmt(ph_start, 3), fontsize=9,
            color=_C_PH, ha="left", va="bottom")
    painted.append("pH0=%s" % H.fmt(ph_start, 3))

    ax.set_xlim(0.0, v_max * 1.02)
    ax.set_ylim(y_lo, y_hi)
    ax.axis("off")
    report = H.finish_panels(fig, [ax], out_path,
                             skip=("$V/\\mathrm{mL}$", "$\\mathrm{pH}$", "$O$"))

    return {
        "equivalence_volume": v_eq,
        "equivalence_pH": ph_eq,
        "initial_pH": ph_start,
        "half_equivalence_pH": pH_at(0.5 * v_eq) if is_weak else None,
        "pKa": -math.log10(K) if is_weak and mode == "acid" else None,
        "pKb": -math.log10(K) if is_weak and mode == "base" else None,
        "marks": set(painted),
        "layout": report,
    }


def equilibrium(v_f0=1.0, v_r0=0.2, v_eq=None, t_change=3.0, jump_f=0.6,
                jump_r=0.0, tau=0.55, t_end=8.0, show_shift=True,
                out_path="chem_equilibrium.png"):
    r"""Forward and reverse rates against time, with one perturbation.

    Before ``t_change`` both rates relax towards ``v_eq`` (the first
    equilibrium); at ``t_change`` the rates jump by ``jump_f``/``jump_r`` and
    then relax towards a *new* common value.  That the two curves end on the
    same horizontal is the definition of equilibrium, and it is asserted here:
    a diagram where they settle at different heights teaches the opposite.
    """
    plt = env.pyplot()
    vf0, vr0 = float(v_f0), float(v_r0)
    t1 = float(t_change)
    jf, jr = float(jump_f), float(jump_r)
    tau = float(tau)
    t_end = float(t_end)
    if tau <= 0:
        raise ValueError("tau must be positive")
    if not 0.0 < t1 < t_end:
        raise ValueError("t_change must lie inside (0, t_end)")
    if vf0 <= 0 or vr0 <= 0:
        raise ValueError("initial rates must be positive")

    # ``registry.coerce`` fills in the declared default, so ``v_eq`` arrives as
    # 0.0 rather than None when the caller omits it.  Treat any non-positive
    # value as "work it out from the two starting rates".
    veq1 = float(v_eq) if v_eq is not None and float(v_eq) > 0 else \
        0.5 * (vf0 + vr0)
    veq2 = veq1 + 0.5 * (jf + jr)

    def relax(v_start, v_target, t0, ts):
        return v_target + (v_start - v_target) * np.exp(-(ts - t0) / tau)

    t_a = np.linspace(0.0, t1, 400)
    vf_a = relax(vf0, veq1, 0.0, t_a)
    vr_a = relax(vr0, veq1, 0.0, t_a)

    t_b = np.linspace(t1, t_end, 500)
    vf_at_change = float(relax(vf0, veq1, 0.0, np.array([t1]))[0]) + jf
    vr_at_change = float(relax(vr0, veq1, 0.0, np.array([t1]))[0]) + jr
    vf_b = relax(vf_at_change, veq2, t1, t_b)
    vr_b = relax(vr_at_change, veq2, t1, t_b)

    # The two rates must meet, and stay met.  The tolerance is *relative to the
    # gap that has to close*: an exponential only approaches its limit, so an
    # absolute 1e-9 would fail on a window that merely stops short of infinity.
    # What matters is that the visible gap is a small fraction of the jump.
    gap_start = abs(vf_at_change - vr_at_change)
    gap_end = abs(vf_b[-1] - vr_b[-1])
    if gap_start > 1e-9 and gap_end >= 0.02 * gap_start:
        # A contradiction in the *parameters*, not an internal invariant: the
        # window ends before the two curves have met.  Raised rather than
        # asserted so it survives ``python -O`` and reads as what it is.
        raise ValueError(
            "the two rates do not settle before t_end: the final gap is %.3g%% "
            "of the initial one, so the window (t_change=%g to t_end=%g) is "
            "shorter than the relaxation time tau=%g.  Lengthen t_end or "
            "shorten tau."
            % (100.0 * gap_end / gap_start, t1, t_end, tau))

    fig, ax = plt.subplots(figsize=(5.4, 3.6), dpi=300)
    painted = []

    v_all = np.concatenate([vf_a, vf_b, vr_a, vr_b])
    y_hi = float(v_all.max()) * 1.20
    y_lo = 0.0

    painted.extend(H.frame(ax, (-0.03 * t_end, t_end * 1.02), (y_lo, y_hi),
                           xlabel="$t$", ylabel="$v$", style="corner"))

    ax.plot(np.concatenate([t_a, t_b]), np.concatenate([vf_a, vf_b]),
            color=_C_FWD, lw=2.0, zorder=4)
    ax.plot(np.concatenate([t_a, t_b]), np.concatenate([vr_a, vr_b]),
            color=_C_REV, lw=2.0, zorder=4)

    ax.text(t_end * 0.86, vf_b[-1] + 0.05 * y_hi, "v正",
            fontsize=10, color=_C_FWD, ha="left", va="bottom")
    ax.text(t_end * 0.86, vr_b[-1] - 0.05 * y_hi, "v逆",
            fontsize=10, color=_C_REV, ha="left", va="top")
    painted += ["v正", "v逆"]

    # The first equilibrium: where the curves first meet.
    #
    # Chinese is written as plain text, never inside ``$...$``.  Mathtext
    # switches to the ``cm`` font set, which has no CJK glyphs, so
    # ``$\mathrm{平衡}$`` renders two tofu boxes -- and matplotlib only warns
    # about it, so the figure saves "successfully" with two empty rectangles in
    # it.
    H.guide(ax, (0.0, veq1), (t_end, veq1), color="#c8c8c8")
    ax.text(t1 * 0.5, veq1 + 0.04 * y_hi, "平衡", fontsize=9.5,
            color="#455a64", ha="center", va="bottom")
    painted.append("平衡")

    if show_shift:
        H.guide(ax, (t1, 0.0), (t1, y_hi), color="#9e9e9e")
        # The jump itself, drawn as a vertical tick so the discontinuity is
        # visible rather than smoothed away by the sampling.
        for v_from, v_to, colour in ((vf_at_change - jf, vf_at_change, _C_FWD),
                                     (vr_at_change - jr, vr_at_change, _C_REV)):
            if abs(v_to - v_from) > 1e-9:
                ax.annotate("", xy=(t1, v_to), xytext=(t1, v_from),
                            arrowprops=dict(arrowstyle="-|>", color=colour,
                                            lw=1.2, mutation_scale=9),
                            zorder=6)
        ax.text(t1, y_hi * 0.97, "$t_1$", fontsize=9.5, ha="center", va="top",
                color="#37474f")
        painted.append("t1")
        H.guide(ax, (0.0, veq2), (t_end, veq2), color="#c8c8c8")
        ax.text(t_end * 0.99, veq2 + 0.04 * y_hi, "新平衡", fontsize=9.5,
                color="#455a64", ha="right", va="bottom")
        painted.append("新平衡")

    ax.set_xlim(-0.03 * t_end, t_end * 1.02)
    ax.set_ylim(y_lo, y_hi)
    ax.axis("off")
    report = H.finish_panels(fig, [ax], out_path,
                             skip=("$t$", "$v$", "$O$", "v正", "v逆", "$t_1$"))

    return {
        "equilibrium_rate_1": veq1,
        "equilibrium_rate_2": veq2,
        "shifted_towards": ("forward" if jf > jr else
                            "reverse" if jr > jf else "none"),
        "marks": set(painted),
        "layout": report,
    }

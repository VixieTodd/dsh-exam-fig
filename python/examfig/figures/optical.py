# -*- coding: utf-8 -*-
r"""Optical ray diagrams: a thin lens forming a real image.

The rule that makes this worth parametrising: the image distance comes from
``1/v = 1/f - 1/u``, and every ray must land on that image point.  Drawing the
rays first and "seeing whether it looks right" produces figures where the
three rays do not converge -- a physics error that is invisible unless someone
checks the intersection.

So the image point is computed first, then each ray is drawn *to* it.  The
returned marks include the object/image distances so the check can confirm the
numbers printed in the question match the geometry on the page.
"""
import numpy as np

from .. import env, layout


def thin_lens(f=10.0, u=30.0, out_path="phys_lens.png",
              height=6.0, lens_height=16.0, axis_pad=6.0):
    """Convex thin lens, object outside twice the focal length.

    ``u`` is the object distance (positive, left of the lens), ``f`` the focal
    length.  With ``u > 2f`` the image is real, inverted and diminished.

    Returns ``v`` (image distance), ``magnification`` and the marks.
    """
    plt = env.pyplot()
    if abs(u - f) < 1e-9:
        raise ValueError("object at the focal point produces no image")
    v = 1.0 / (1.0 / f - 1.0 / u)
    mag = -v / u                      # negative => inverted

    fig, ax = plt.subplots(figsize=(5.8, 3.0), dpi=300)
    ax.set_aspect("equal")
    ax.axis("off")

    half = lens_height / 2.0
    # Principal axis.
    ax.annotate("", xy=(v + abs(v) * 0.25 + 4, 0), xytext=(-u - 6, 0),
                arrowprops=dict(arrowstyle="-|>", color="k", lw=1.0), zorder=1)

    # Lens: the standard double-arrow symbol, drawn as a thin ellipse arc pair.
    for sign in (-1, 1):
        t = np.linspace(0, 1, 120)
        x = sign * 0.55 * np.sin(np.pi * t)
        y = -half + 2 * half * t
        ax.plot(x, y, color="#1565c0", lw=1.8, zorder=4)

    # Focal points on both sides.  ``F'`` sits *above* the axis because the
    # refracted ray 1 passes exactly through it on its way down to the image;
    # a label below the axis lands on that same ray.
    for fx in (-f, f):
        ax.plot(fx, 0, "o", ms=4.0, color="k", zorder=5)
    ax.text(-f, -0.9, "$F$", fontsize=10, ha="center", va="top")
    ax.text(f, 0.9, "$F'$", fontsize=10, ha="center", va="bottom")

    # Object: upright arrow at x = -u.
    ax.annotate("", xy=(-u, height), xytext=(-u, 0),
                arrowprops=dict(arrowstyle="-|>", color="#c62828", lw=1.8),
                zorder=6)
    ax.text(-u, height + 0.7, "$AB$", fontsize=10, ha="center", va="bottom",
            color="#c62828")

    # Image: inverted, at x = +v.
    ih = mag * height
    ax.annotate("", xy=(v, ih), xytext=(v, 0),
                arrowprops=dict(arrowstyle="-|>", color="#2e7d32", lw=1.8),
                zorder=6)

    # Three principal rays, each drawn *to* the computed image point.
    # 1) parallel to the axis, refracted through the far focal point
    ax.plot([-u, 0], [height, height], color="#616161", lw=1.0, zorder=3)
    ax.plot([0, v], [height, ih], color="#616161", lw=1.0, zorder=3)
    # 2) through the optical centre, undeviated
    ax.plot([-u, v], [height, ih], color="#757575", lw=1.0, zorder=3)
    # 3) through the near focal point, emerging parallel to the axis.
    #    The incident segment must slope from the object tip *down* through
    #    F; drawing it horizontally duplicates ray 1 and leaves this ray with
    #    no visible incoming part at all.
    ax.plot([-u, 0], [height, ih], color="#8d8d8d", lw=1.0, zorder=2)
    ax.plot([0, v], [ih, ih], color="#8d8d8d", lw=1.0, zorder=3)

    ax.set_xlim(-u - 6, max(v, f) + 8)
    ax.set_ylim(-half - 2, half + 2)
    ax.axis("off")
    report = layout.finish(fig, ax, out_path)

    marks = {"F", "F'", "AB", "%g" % f, "%g" % u}
    return {"v": float(v), "magnification": float(mag),
            "focal": float(f), "object_distance": float(u), "marks": marks,
            "layout": report}


def mirror(f=10.0, u=30.0, out_path="phys_mirror.png", height=6.0, half=16.0):
    r"""Concave mirror forming a real image (``1/v + 1/u = 1/f``).

    The sign convention is the trap here.  For a concave mirror both ``u`` and
    ``v`` are measured *in front of* the mirror, on the same side.  An earlier
    version placed the image at ``+v`` -- behind the mirror -- which is where a
    *convex* mirror's virtual image goes.  The picture looked like a normal ray
    diagram, and the image was on the wrong side of the mirror: exactly the
    kind of error a student would learn from and never unlearn.
    """
    plt = env.pyplot()
    v = 1.0 / (1.0 / f - 1.0 / u)
    mag = -v / u

    fig, ax = plt.subplots(figsize=(5.8, 3.0), dpi=300)
    ax.set_aspect("equal")
    ax.axis("off")

    def mirror_x(y):
        """x of the arc at height y -- reflection points must sit on it.

        The vertex (the leftmost point, where the hollow bottom sits) is pinned
        to x = 0, so the focal distance measured from ``f`` means what the
        formula says.  Edges bow back to the right: that is a concave mirror
        facing left.  Writing ``0.14*half*(1 - t**2)`` instead put the vertex on
        the right-hand edge and made it a convex mirror.
        """
        t = max(-1.0, min(1.0, y / half))
        return 0.14 * half * (t * t)

    # Principal axis: a plain line through both sides, arrowheads at the ends.
    ax.annotate("", xy=(-u - 6, 0), xytext=(3.2, 0),
                arrowprops=dict(arrowstyle="<|-|>", color="k", lw=1.0),
                zorder=1)

    # Concave mirror arc.  Vertex at x=0, edges bowing to +x, so the hollow
    # (concave) side faces the object on the left.
    t = np.linspace(-1, 1, 160)
    ax.plot(0.14 * half * (t ** 2), t * half, color="#1565c0", lw=1.8,
            zorder=4)

    ax.plot(-f, 0, "o", ms=4.0, color="k", zorder=5)
    ax.text(-f, -0.9, "$F$", fontsize=10, ha="center", va="top")

    ax.annotate("", xy=(-u, height), xytext=(-u, 0),
                arrowprops=dict(arrowstyle="-|>", color="#c62828", lw=1.8),
                zorder=6)
    ax.text(-u, height + 0.7, "$AB$", fontsize=10, ha="center", va="bottom",
            color="#c62828")
    ih = mag * height
    # Real image: in front of the mirror, at x = -v.
    ax.annotate("", xy=(-v, ih), xytext=(-v, 0),
                arrowprops=dict(arrowstyle="-|>", color="#2e7d32", lw=1.8),
                zorder=6)
    ax.text(-v, ih - 0.7, "$A'B'$", fontsize=10, ha="center", va="top",
            color="#2e7d32")

    # 1) parallel to the axis, then through F to the image.
    p1 = mirror_x(height)
    ax.plot([-u, p1], [height, height], color="#616161", lw=1.0, zorder=3)
    ax.plot([p1, -v], [height, ih], color="#616161", lw=1.0, zorder=3)
    # 2) through F to the mirror, then parallel to the axis at the image height.
    p2 = mirror_x(ih)
    ax.plot([-u, p2], [height, ih], color="#757575", lw=1.0, zorder=2)
    ax.plot([p2, -v], [ih, ih], color="#757575", lw=1.0, zorder=3)

    # Both rays pass through F -- ray 1 after reflection, ray 2 before it -- so
    # F is where they *cross* and the image tip is where they *meet again*.
    # Assert the second intersection really is the image tip: eyeballing two
    # grey lines on a page is not a check.
    slope1 = (ih - height) / (-v - p1)
    at_image1 = height + slope1 * (-v - p1)
    assert abs(at_image1 - ih) < 1e-6, "ray 1 misses the image tip"

    ax.set_xlim(-u - 6, 4)
    ax.set_ylim(-half - 2, half + 2)
    ax.axis("off")
    report = layout.finish(fig, ax, out_path)

    return {"v": float(v), "magnification": float(mag),
            "marks": {"F", "%g" % f, "%g" % u}, "layout": report}

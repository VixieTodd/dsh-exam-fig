# -*- coding: utf-8 -*-
"""Engine tests: the part that actually draws.

Run with the plugin's own interpreter and a populated vendor directory:

    python -m examfig.figdeps          # once, to fetch the dependencies
    python tests/test_engine.py

Deliberately dependency-free -- no pytest.  The environments this plugin
targets often cannot install one, and a test suite that cannot start is not a
test suite.  Every case asserts on *numbers the drawing function returns*, not
on pixels: ``incline`` reports ``ratio == tan(theta)``, ``mirror`` reports the
image distance, ``chem`` reports the subscript flags.  A pixel test would pass
on a beautifully drawn wrong figure -- which is exactly the failure this
project exists to prevent.
"""
import os
import sys


HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "python"))

from examfig import env  # noqa: E402

env.bootstrap()

_failures = []


def check(label, condition, detail=""):
    if condition:
        print("  PASS  %s" % label)
    else:
        _failures.append(label)
        print("  FAIL  %s%s" % (label, (" -- %s" % detail) if detail else ""))


def approx(a, b, tol=1e-6):
    try:
        return abs(float(a) - float(b)) <= tol
    except (TypeError, ValueError):
        return False


def test_env():
    print("\nenvironment")
    info = env.bootstrap()
    check("vendor directory resolved", bool(info["vendor"]), str(info["vendor"]))
    font = env.configure_matplotlib()
    check("a CJK font is available", bool(font), str(font))
    packages = env.installed_packages()
    for name, version in sorted(packages.items()):
        check("package %s" % name, version is not None, "missing")
    print("        font=%s python=%s" % (font, info["version"]))


def test_registry():
    print("\nregistry")
    from examfig import registry

    names = registry.names()
    check("nine kinds registered", len(names) == 9, ", ".join(names))
    for expected in ("quadratic", "triangle", "cube", "pyramid", "incline",
                     "circuit", "lens", "mirror", "molecule"):
        check("kind %s present" % expected, expected in names)

    # Unknown parameters must be refused, not silently dropped: a caller who
    # misspells ``theta_deg`` and gets a 30-degree figure back has no way to
    # notice.
    try:
        registry.coerce("incline", {"nope": 1})
        check("unknown parameter rejected", False, "no exception")
    except ValueError as exc:
        check("unknown parameter rejected", "nope" in str(exc), str(exc))

    try:
        registry.coerce("nonexistent", {})
        check("unknown kind rejected", False, "no exception")
    except KeyError:
        check("unknown kind rejected", True)

    # Defaults must round-trip through coerce.
    kwargs = registry.coerce("quadratic", {})
    check("defaults applied", kwargs == {"a": 1.0, "b": -2.0, "c": -3.0}, str(kwargs))


def test_figures(tmpdir):
    print("\nfigures")
    from examfig import registry

    cases = {
        "quadratic": ({}, lambda r: (
            approx(r["vertex"][0], 1.0) and approx(r["vertex"][1], -4.0)
            and sorted(round(x, 6) for x in r["roots"]) == [-1.0, 3.0])),
        "triangle": ({"ac": 3, "bc": 4}, lambda r: (
            approx(r["hypotenuse"], 5.0) and r["right_angle_at"] == "C")),
        "cube": ({}, lambda r: approx(r["diagonal"], 3 ** 0.5)),
        "pyramid": ({}, lambda r: approx(r["height"], 1.05)),
        "incline": ({"theta_deg": 30}, lambda r: (
            approx(r["ratio"], 0.5773502691896257)
            and approx(r["G_par"], r["G_perp"] * r["ratio"]))),
        "circuit": ({"emf": 6, "r1": 2, "r2": 4}, lambda r: (
            approx(r["current"], 1.0) and r["loop_closed"] is True)),
        "lens": ({"f": 10, "u": 30, "height": 6}, lambda r: (
            approx(r["v"], 15.0) and approx(r["magnification"], -0.5))),
        "mirror": ({"f": 10, "u": 30, "height": 6}, lambda r: (
            approx(r["v"], 15.0) and approx(r["magnification"], -0.5))),
        "molecule": ({"smiles_list": ["CCO", "CC(=O)O"]}, lambda r: (
            r["formulas"] == ["C2H6O", "C2H4O2"])),
    }

    for kind, (params, predicate) in cases.items():
        out = os.path.join(tmpdir, kind + ".png")
        try:
            result = registry.draw(kind, params, out)
        except Exception as exc:                  # noqa: BLE001 - reported
            check("%s draws" % kind, False, "%s: %s" % (type(exc).__name__, exc))
            continue
        check("%s draws" % kind, os.path.isfile(out) and os.path.getsize(out) > 2000,
              "%s bytes" % (os.path.getsize(out) if os.path.isfile(out) else 0))
        # PNG signature, not just "a file appeared".
        with open(out, "rb") as f:
            check("%s is a PNG" % kind, f.read(8) == b"\x89PNG\r\n\x1a\n")
        check("%s numbers correct" % kind, bool(predicate(result)), str(result)[:160])
        check("%s reports marks" % kind,
              isinstance(result.get("marks"), (set, list, tuple))
              and len(result["marks"]) > 0)


def test_figcheck():
    print("\nfigure/question consistency")
    from examfig import figcheck

    # A correct pair passes.
    ok, lines = figcheck.check(
        [{"no": 1, "need": ["G", "G_par", "G_perp", "30"], "text": "如图1"}],
        {1: {"marks": ["G", "Gpar", "Gperp", "30"]}})
    check("matching labels pass", ok, " | ".join(lines))

    # A missing label fails and is named.  Note ``G`` alone: a one-letter
    # requirement must not be satisfied by ``Gperp``, which is a real false
    # pass the length guard exists to prevent.
    ok, lines = figcheck.check(
        [{"no": 1, "need": ["G", "G_par", "G_perp"], "text": "如图1"}],
        {1: {"marks": ["G", "Gpar"]}})
    check("missing label fails", not ok, " | ".join(lines))
    check("missing label named", any("G_perp" in ln or "Gperp" in ln for ln in lines),
          " | ".join(lines))

    # A single-character requirement is not satisfied by a longer mark.
    ok, _ = figcheck.check(
        [{"no": 1, "need": ["G"]}], {1: {"marks": ["Gperp"]}})
    check("one-letter requirement is not a substring match", not ok)

    # ... but a bare digit *is* satisfied by "6 V": the extra text is a unit,
    # and reporting a miss there sends the caller hunting for a label that is
    # plainly on the page.  This was a real false failure.
    ok, lines = figcheck.check(
        [{"no": 2, "need": ["R_1", "R_2", "6"]}],
        {2: {"marks": ["6 V", "R_1=2", "R_2=4"]}})
    check("digit matches a valued label", ok, " | ".join(lines))

    # The real bug this caught: the right angle drawn on the wrong vertex.
    ok, lines = figcheck.check(
        [{"no": 2, "need": ["A", "B", "C", "90"], "text": "Rt△ABC，∠C=90°"}],
        {2: {"marks": ["A", "B", "C", "right_angle_at_A"]}})
    check("wrong-vertex right angle fails", not ok, " | ".join(lines))

    # Spelling variants must fold together.
    ok, _ = figcheck.check(
        [{"no": 3, "need": ["G_{\\parallel}", "30^{\\circ}"]}],
        {3: {"marks": ["G∥", "30°"]}})
    check("LaTeX and Unicode fold together", ok)

    # A stem referencing a figure that was never drawn.
    ok, lines = figcheck.check([{"no": 4, "need": [], "text": "如图 7 所示"}], {4: {"marks": []}})
    check("dangling 图 N reference fails", not ok, " | ".join(lines))

    # Benign axis labels must not drag a question into a false failure.
    ok, _ = figcheck.check(
        [{"no": 5, "need": ["O", "x", "y", "顶点"]}],
        {5: {"marks": ["O", "x", "y", "顶点"]}})
    check("benign labels do not cause a false failure", ok)


def test_chem():
    print("\nchemistry")
    from examfig import chem

    # Coalescing means a contiguous non-subscript run arrives as one piece, so
    # "2H2O" -> [("2H", False), ("2", True), ("O", False)].  That is the
    # intended shape: the document gets one run per visual stretch, not per
    # character.
    runs = chem.parse_formula("2H2O")
    check("leading coefficient stays full size",
          runs[0] == ("2H", False), str(runs))
    check("water subscript correct",
          runs == [("2H", False), ("2", True), ("O", False)], str(runs))

    cases = {
        "Ca(OH)2": [("Ca(OH)", False), ("2", True)],
        "Al2(SO4)3": [("Al", False), ("2", True), ("(SO", False),
                      ("4", True), (")", False), ("3", True)],
        "2KClO3": [("2KClO", False), ("3", True)],
        "H2SO4": [("H", False), ("2", True), ("SO", False), ("4", True)],
    }
    for formula, expected in cases.items():
        got = chem.parse_formula(formula)
        check("%s subscripts" % formula, got == expected, str(got))

    # Inorganic uses "=", organic uses "->" -- a hard requirement of the
    # textbooks this plugin serves.
    inorganic = chem.equation_parts("2H2", "2H2O", condition="\u70b9\u71c3", organic=False)
    check("inorganic uses =",
          any(k == "t" and "=" in v for k, v in inorganic), str(inorganic))
    organic = chem.equation_parts("C2H5OH", "CO2", condition="\u70b9\u71c3", organic=True)
    check("organic uses ->",
          any(k == "t" and "\u2192" in v for k, v in organic), str(organic))

    # The condition sits between two symbols, per the textbook.
    check("condition repeated",
          any(k == "t" and v.count("=") == 2 for k, v in inorganic), str(inorganic))


def test_omml():
    print("\nequations (OMML)")
    from examfig import omml

    if not omml.available():
        print("  SKIP  MML2OMML.XSL not found (Microsoft Office is not installed)")
        return
    path = omml.find_stylesheet()
    check("stylesheet located", bool(path), str(path))
    try:
        node = omml.tex2omml(r"y=x^{2}-2x-3")
        check("oMath produced", node.tag.endswith("}oMath"), node.tag)
    except Exception as exc:                      # noqa: BLE001 - reported
        check("oMath produced", False, "%s: %s" % (type(exc).__name__, exc))


def test_layout(tmpdir):
    print("\nlayout: collision audit and repair")
    from examfig import layout

    plt = env.pyplot()

    def fresh(xlim=(0, 10), ylim=(0, 10)):
        fig, ax = plt.subplots(figsize=(4, 3), dpi=100)
        ax.set_xlim(*xlim)
        ax.set_ylim(*ylim)
        ax.axis("off")
        return fig, ax

    # Two labels at the same point overlap; the audit must say so.
    fig, ax = fresh()
    ax.text(5.0, 5.0, "hello", fontsize=12, ha="center", va="center")
    ax.text(5.0, 5.0, "world", fontsize=12, ha="center", va="center")
    fig.canvas.draw()
    found = layout.audit(ax)
    check("overlapping labels reported",
          any(c["kind"] == layout.SEV_OVERLAP for c in found),
          str(found))
    check("overlap names both labels",
          all(any(c["a"] == n or c["b"] == n for c in found) for n in ("hello", "world")),
          str(found))
    plt.close(fig)

    # Two labels far apart: nothing to report.  This is the check that stops
    # the auditor from crying wolf on every figure.
    fig, ax = fresh()
    ax.text(1.0, 1.0, "aaa", fontsize=12, ha="center", va="center")
    ax.text(9.0, 9.0, "bbb", fontsize=12, ha="center", va="center")
    fig.canvas.draw()
    check("separated labels are clean", layout.audit(ax) == [], str(layout.audit(ax)))
    plt.close(fig)

    # Repair actually separates them.
    fig, ax = fresh()
    a = ax.text(5.0, 5.0, "first", fontsize=12, ha="center", va="center")
    b = ax.text(5.0, 5.0, "second", fontsize=12, ha="center", va="center")
    fig.canvas.draw()
    before, after, moved = layout.resolve(ax)
    check("repair finds something to move", bool(moved), str(moved))
    check("repair removes the overlap",
          not any(c["kind"] == layout.SEV_OVERLAP for c in after), str(after))
    plt.close(fig)

    # A label outside the frame is reported, and `resolve` may move it back in.
    fig, ax = fresh()
    ax.text(10.6, 5.0, "outside", fontsize=12, ha="center", va="center")
    fig.canvas.draw()
    check("out-of-frame label reported",
          any(c["kind"] == layout.SEV_FRAME for c in layout.audit(ax)))
    plt.close(fig)

    # `skip` exempts a label from the line and frame checks but NOT from
    # overlap: an angle mark belongs on its rays, two words do not belong on
    # each other.
    fig, ax = fresh()
    ax.plot([0, 10], [5, 5], "k-")
    ax.text(5.0, 5.0, "on-the-line", fontsize=12, ha="center", va="center")
    fig.canvas.draw()
    check("label on a line reported",
          any(c["kind"] == layout.SEV_LINE for c in layout.audit(ax)))
    check("skip exempts it",
          layout.audit(ax, skip=("on-the-line",)) == [],
          str(layout.audit(ax, skip=("on-the-line",))))
    plt.close(fig)

    # An empty annotation is an arrow, not a label: treating it as text would
    # report every arrowhead as a collision.
    fig, ax = fresh()
    ax.annotate("", xy=(8, 8), xytext=(2, 2),
                arrowprops=dict(arrowstyle="-|>", color="k"))
    ax.text(5.0, 5.0, "x", fontsize=12, ha="center", va="center")
    fig.canvas.draw()
    check("empty annotation is not a label",
          [t for _a, t in layout.labels(ax)] == ["x"],
          str(layout.labels(ax)))
    plt.close(fig)

    # Marker-only lines draw dots, not strokes; they must not count as
    # obstacles or every vertex dot would push its own label away.
    fig, ax = fresh()
    ax.plot([5], [5], "ko", ms=6)
    ax.text(5.0, 5.0, "vertex", fontsize=12, ha="center", va="center")
    fig.canvas.draw()
    check("marker-only plot is not an obstacle",
          not any(c["kind"] == layout.SEV_LINE for c in layout.audit(ax)),
          str(layout.audit(ax)))
    plt.close(fig)

    # `finish` saves and reports in one go.
    out = os.path.join(tmpdir, "layout_finish.png")
    fig, ax = fresh()
    ax.text(4.9, 5.0, "left", fontsize=12, ha="center", va="center")
    ax.text(5.1, 5.0, "right", fontsize=12, ha="center", va="center")
    report = layout.finish(fig, ax, out)
    check("finish writes a PNG",
          os.path.isfile(out) and os.path.getsize(out) > 1000,
          str(os.path.getsize(out) if os.path.isfile(out) else 0))
    check("finish reports the shape",
          set(report) == {"collisions", "fixed", "remaining"}, str(report))
    check("finish left no collisions", report["collisions"] == 0, str(report))


def test_figure_layout_reports(tmpdir):
    print("\nfigures: every drawing reports its layout")
    from examfig import registry

    for kind in registry.names():
        out = os.path.join(tmpdir, "lay_" + kind + ".png")
        try:
            result = registry.draw(kind, {}, out)
        except Exception as exc:                  # noqa: BLE001 - reported
            check("%s draws for layout" % kind, False, "%s: %s" % (type(exc).__name__, exc))
            continue
        report = result.get("layout")
        check("%s reports layout" % kind, isinstance(report, dict), str(report))
        if not isinstance(report, dict):
            continue
        check("%s has no unresolved collision" % kind,
              report.get("collisions") == 0, str(report))


def main():
    print("examfig engine tests")
    # Not tempfile.mkdtemp(): the DSH file sandbox allows creating that
    # directory but denies writing a PNG into it, so every drawing test would
    # fail with PermissionError regardless of whether the code works.  Draw
    # into a scratch directory beside the tests instead.
    tmpdir = os.path.join(HERE, ".scratch")
    os.makedirs(tmpdir, exist_ok=True)
    try:
        test_env()
        test_registry()
        test_figures(tmpdir)
        test_figcheck()
        test_chem()
        test_layout(tmpdir)
        test_figure_layout_reports(tmpdir)
        test_omml()
    finally:
        import shutil
        shutil.rmtree(tmpdir, ignore_errors=True)

    print("\n%s" % ("ALL PASS" if not _failures else "%d FAILURE(S): %s"
                    % (len(_failures), ", ".join(_failures))))
    return 0 if not _failures else 1


if __name__ == "__main__":
    raise SystemExit(main())

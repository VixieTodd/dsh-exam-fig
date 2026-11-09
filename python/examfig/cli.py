# -*- coding: utf-8 -*-
"""Command line entry point.

The DSH plugin spawns this script rather than importing the package, because
the harness decides which Python to run and this process must control its own
``sys.path`` before any heavy import happens.

Every subcommand prints one JSON object on stdout, so the caller never has to
parse prose or scrape a traceback.  Progress and warnings go to stderr.

    doctor                      report the environment
    catalog                     list figure kinds and their parameters
    draw --kind K --out F       draw a figure
    check --spec F              verify question/figure consistency
"""
import argparse
import json
import os
import sys
import traceback


def _json_default(obj):
    """Make drawing results serialisable.

    The drawing functions return sets, tuples and numpy scalars -- all
    meaningful in Python, none of them JSON.  Converting here keeps the
    functions free of serialisation concerns.
    """
    if isinstance(obj, (set, frozenset)):
        return sorted(obj)
    if isinstance(obj, tuple):
        return list(obj)
    for attr in ("item",):                        # numpy scalar
        method = getattr(obj, attr, None)
        if callable(method):
            try:
                return method()
            except Exception:                     # noqa: BLE001 - fall through
                break
    if isinstance(obj, bytes):
        return obj.decode("utf-8", "replace")
    return str(obj)


def _emit(obj):
    sys.stdout.write(json.dumps(obj, ensure_ascii=False, default=_json_default))
    sys.stdout.write("\n")
    sys.stdout.flush()


def cmd_doctor(args):
    from . import env, omml, figdeps

    info = env.bootstrap()
    # This tool exists to *report* a broken install, so a missing dependency
    # must not be what breaks it.  Without this guard, `doctor` is the one tool
    # that cannot be used when it is most needed -- which is exactly how it
    # shipped the first time.
    try:
        font = env.configure_matplotlib()
    except Exception as exc:                      # noqa: BLE001 - reported below
        font = None
        matplotlib_error = "%s: %s" % (type(exc).__name__, exc)
    else:
        matplotlib_error = None

    try:
        packages = env.installed_packages()
    except Exception:                             # noqa: BLE001 - degraded report
        packages = {}

    report = {
        "ok": True,
        "python": info["version"],
        "executable": info["python"],
        "vendor": info["vendor"],
        "mplCacheDir": info["mplCacheDir"],
        "font": font,
        "packages": packages,
        "omml": omml.available(),
        "mml2omml": omml.find_stylesheet(),
        "mirrors": figdeps.MIRRORS[:3],
    }
    missing = [k for k, v in packages.items() if v is None]
    report["missing"] = missing
    if missing:
        report["ok"] = False
        report["hint"] = ("Run: python -m examfig.figdeps %s" % " ".join(missing))
    if matplotlib_error:
        report["ok"] = False
        report["hint"] = ("matplotlib is not importable (%s). Run: "
                          "python -m examfig.figdeps matplotlib numpy" % matplotlib_error)
    if not report["omml"]:
        report["warning"] = (
            "MML2OMML.XSL not found; equations fall back to plain text. "
            "It ships with Microsoft Office."
        )
    if not font and not matplotlib_error:
        report["warning"] = (
            "No CJK font found; Chinese labels will render as boxes. "
            "Install Noto Sans CJK SC or set DSH_EXAMFIG_..."
        )
    _emit(report)


def cmd_catalog(args):
    from . import registry
    _emit({"ok": True, "kinds": registry.catalog()})


def cmd_draw(args):
    from . import env, registry

    params = json.loads(args.params) if args.params else {}
    out = os.path.abspath(args.out)
    parent = os.path.dirname(out)
    if parent:
        os.makedirs(parent, exist_ok=True)

    env.bootstrap()
    result = registry.draw(args.kind, params, out)
    marks = result.get("marks")
    if isinstance(marks, (set, frozenset)):
        marks = sorted(marks)
    payload = dict(result)
    payload["marks"] = marks
    payload["path"] = out
    payload["bytes"] = os.path.getsize(out)
    payload["ok"] = True
    _emit(payload)


def cmd_check(args):
    from . import figcheck

    with open(args.spec, "r", encoding="utf-8") as f:
        data = json.load(f)
    specs = data.get("specs") or []
    figures = {}
    for key, value in (data.get("figures") or {}).items():
        figures[int(key)] = value
    ok, lines = figcheck.check(specs, figures)
    _emit({"ok": ok, "lines": lines})


def cmd_latex(args):
    """Turn LaTeX into an OMML snippet, for the JS side to splice into XML."""
    from . import omml
    from lxml import etree

    node = omml.tex2omml(args.tex)
    _emit({"ok": True, "xml": etree.tostring(node, encoding="unicode")})


def cmd_chem(args):
    """Chemical formula runs: ``[{'text': 'H', 'sub': false}, ...]``."""
    from . import chem

    runs = [{"text": t, "sub": bool(s)} for t, s in chem.parse_formula(args.formula)]
    payload = {"ok": True, "runs": runs}
    if args.equation:
        lhs, rhs = args.equation
        payload["equation"] = chem.equation(
            lhs, rhs, args.condition or "", organic=not args.inorganic)
        payload["parts"] = [
            {"kind": k, "value": ([[t, bool(s)] for t, s in v] if k == "c" else v)}
            for k, v in chem.equation_parts(
                lhs, rhs, args.condition or "", organic=not args.inorganic)
        ]
    _emit(payload)


def main(argv=None):
    parser = argparse.ArgumentParser(prog="examfig", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("doctor", help="report the environment")
    p.set_defaults(func=cmd_doctor)

    p = sub.add_parser("catalog", help="list figure kinds")
    p.set_defaults(func=cmd_catalog)

    p = sub.add_parser("draw", help="draw one figure")
    p.add_argument("--kind", required=True)
    p.add_argument("--params", default="{}", help="JSON object of parameters")
    p.add_argument("--out", required=True)
    p.set_defaults(func=cmd_draw)

    p = sub.add_parser("check", help="verify question/figure consistency")
    p.add_argument("--spec", required=True, help="path to a JSON spec file")
    p.set_defaults(func=cmd_check)

    p = sub.add_parser("latex", help="LaTeX -> OMML XML")
    p.add_argument("--tex", required=True)
    p.set_defaults(func=cmd_latex)

    p = sub.add_parser("chem", help="chemical formula runs")
    p.add_argument("--formula", default="")
    p.add_argument("--equation", nargs=2, metavar=("LHS", "RHS"))
    p.add_argument("--condition", default="")
    p.add_argument("--inorganic", action="store_true")
    p.set_defaults(func=cmd_chem)

    args = parser.parse_args(argv)
    try:
        args.func(args)
    except Exception as exc:                      # noqa: BLE001 - reported as JSON
        # The traceback goes to stderr, not into the JSON.  Callers validate
        # the reply against a declared schema, and a field nobody declared
        # makes the whole tool call fail with "invalid output" -- turning a
        # useful error into an unreadable one.  One shape, everywhere:
        # `{ok: false, error: "..."}`.
        sys.stderr.write(traceback.format_exc())
        _emit({"ok": False, "error": "%s: %s" % (type(exc).__name__, exc)})
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

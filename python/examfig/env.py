# -*- coding: utf-8 -*-
"""Runtime bootstrap shared by every entry point.

Three environment problems are solved here, all of them discovered the hard
way on a sandboxed DSH install:

1. **Where the dependencies live.**  DSH ships its own Python whose
   ``site-packages`` is not writable, and ``pip`` dies inside the file sandbox
   (it can create a directory with ``mkdtemp`` but then cannot write a file
   into it).  Wheels are therefore unpacked into a plain directory that gets
   prepended to ``sys.path`` here.  Lookup order:

       $DSH_EXAMFIG_VENDOR  ->  <plugin>/python/vendor  ->
       $DSH_HOME/exam-fig/vendor  ->  ~/.dsh/exam-fig/vendor

2. **Where matplotlib writes its cache.**  Left alone it uses
   ``%TEMP%/matplotlib-*`` and then fails to delete it, printing a
   ``PermissionError`` traceback on every exit.  ``MPLCONFIGDIR`` is pinned to
   a writable directory instead.

3. **Which CJK font to use.**  Figure labels are Chinese, and the font name
   differs on Windows / macOS / Linux.  Probe what is actually installed
   instead of hard-coding "Microsoft YaHei", which silently degrades to tofu
   boxes everywhere else.
"""
import importlib.util
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PY_ROOT = os.path.dirname(HERE)          # <plugin>/python
PLUGIN_ROOT = os.path.dirname(PY_ROOT)   # <plugin>

# Ordered by preference.  The first one matplotlib actually sees wins.
_CJK_CANDIDATES = (
    "Microsoft YaHei",       # Windows, Simplified Chinese
    "SimHei",                # Windows, classic
    "Microsoft JhengHei",    # Windows, Traditional Chinese
    "SimSun",
    "Source Han Sans SC",
    "Noto Sans CJK SC",
    "Noto Sans SC",
    "PingFang SC",           # macOS
    "Heiti SC",
    "WenQuanYi Zen Hei",     # Linux
    "Arial Unicode MS",
    "DejaVu Sans",           # last resort: no CJK, but always present
)

_cfg = {"vendor": None, "font": None, "bootstrap": None}


def _is_writable(path):
    try:
        os.makedirs(path, exist_ok=True)
        probe = os.path.join(path, ".write-probe")
        with open(probe, "w", encoding="utf-8") as f:
            f.write("ok")
    except OSError:
        return False
    try:
        os.remove(probe)
    except OSError:
        pass
    return True


def vendor_candidates():
    """Every place a dependency bundle may live, most specific first."""
    out = []
    env = os.environ.get("DSH_EXAMFIG_VENDOR")
    if env:
        out.append(env)
    out.append(os.path.join(PY_ROOT, "vendor"))
    home = os.environ.get("DSH_HOME")
    if home:
        out.append(os.path.join(home, "exam-fig", "vendor"))
    out.append(os.path.join(os.path.expanduser("~"), ".dsh", "exam-fig", "vendor"))
    return out


def vendor_dir(create=True):
    """First existing vendor dir; otherwise create the preferred one."""
    if _cfg["vendor"]:
        return _cfg["vendor"]
    cands = vendor_candidates()
    for c in cands:
        if os.path.isdir(c):
            _cfg["vendor"] = c
            return c
    for c in cands[:2]:
        if create and _is_writable(c):
            _cfg["vendor"] = c
            return c
    return None


def _mpl_cache_dir(vendor):
    cands = []
    if os.environ.get("DSH_EXAMFIG_CACHE"):
        cands.append(os.environ["DSH_EXAMFIG_CACHE"])
    if vendor:
        cands.append(os.path.join(os.path.dirname(vendor), ".mplcache"))
    cands.append(os.path.join(os.path.expanduser("~"), ".dsh", "exam-fig", "mplcache"))
    import tempfile
    cands.append(os.path.join(tempfile.gettempdir(), "dsh-exam-fig-mplcache"))
    for c in cands:
        if _is_writable(c):
            return c
    return cands[-1]


def bootstrap():
    """Make the dependency bundle importable and pin matplotlib's cache dir."""
    if _cfg["bootstrap"] is not None:
        return _cfg["bootstrap"]
    v = vendor_dir()
    if v and v not in sys.path:
        sys.path.insert(0, v)
    os.environ.setdefault("MPLCONFIGDIR", _mpl_cache_dir(v))
    _cfg["bootstrap"] = {
        "vendor": v,
        "mplCacheDir": os.environ.get("MPLCONFIGDIR"),
        "python": sys.executable,
        "version": "%d.%d.%d" % sys.version_info[:3],
    }
    return _cfg["bootstrap"]


def configure_matplotlib():
    """Agg backend + a CJK font that actually exists + sane defaults.

    Returns the chosen font family name (or ``None`` when no CJK font was
    found, in which case Chinese labels will render as boxes -- the caller
    should surface that as a warning rather than fail).
    """
    bootstrap()
    import matplotlib
    matplotlib.use("Agg")
    from matplotlib import font_manager
    import matplotlib.pyplot as plt

    if _cfg["font"] is None:
        installed = {f.name for f in font_manager.fontManager.ttflist}
        for name in _CJK_CANDIDATES:
            if name in installed:
                _cfg["font"] = name
                break
        else:
            _cfg["font"] = ""

    family = [_cfg["font"]] if _cfg["font"] else []
    plt.rcParams["font.sans-serif"] = family + ["DejaVu Sans"]
    plt.rcParams["axes.unicode_minus"] = False
    # Computer Modern for mathtext: it is what Chinese textbooks use for
    # variable names and matches Cambria Math far better than DejaVu.
    plt.rcParams["mathtext.fontset"] = "cm"
    plt.rcParams["figure.dpi"] = 300
    plt.rcParams["savefig.dpi"] = 300
    return _cfg["font"] or None


def font_name():
    return _cfg["font"]


def pyplot():
    """The configured ``matplotlib.pyplot``.

    Every drawing module goes through this so that ``bootstrap`` and
    ``configure_matplotlib`` cannot be forgotten.
    """
    configure_matplotlib()
    import matplotlib.pyplot as plt
    return plt


def patches():
    """``matplotlib.patches``, for ``Polygon``/``Circle``/etc."""
    configure_matplotlib()
    import matplotlib.patches as mpatches
    return mpatches


# Which distribution provides which import name.  Used by ``doctor`` to say
# *what to install* instead of just "ImportError".
PACKAGE_IMPORTS = {
    "matplotlib": "matplotlib",
    "numpy": "numpy",
    "python-docx": "docx",
    "lxml": "lxml",
    "latex2mathml": "latex2mathml",
    "rdkit": "rdkit",
    "schemdraw": "schemdraw",
}


def installed_packages():
    """{distribution: version | None} — None means not importable."""
    out = {}
    for dist, mod in PACKAGE_IMPORTS.items():
        if importlib.util.find_spec(mod) is None:
            out[dist] = None
            continue
        try:
            from importlib.metadata import version
            out[dist] = version(dist)
        except Exception:                      # noqa: BLE001 - metadata may be absent
            out[dist] = "unknown"
    return out

# -*- coding: utf-8 -*-
"""Install wheels into the vendor directory without pip.

Why this exists at all: on a sandboxed DSH install, ``pip`` cannot work.  It
downloads into ``tempfile.mkdtemp()`` and then writes the wheel inside that
directory; the file sandbox allows creating the directory but denies writing a
file into it, so every install dies with ``PermissionError`` regardless of
network.  ``site-packages`` is equally unwritable, so a ``.pth`` shim is not an
option either.

So: read the simple index from a mirror, resolve ``Requires-Dist`` by hand,
and extract wheels straight into a plain directory that
:func:`examfig.env.bootstrap` puts on ``sys.path``.

Mirrors are tried in order.  PyPI's own CDN is deliberately last: from mainland
China it drops long transfers with ``SSL: UNEXPECTED_EOF_WHILE_READING`` often
enough that a 9 MB wheel never completes.
"""
import io
import os
import re
import ssl
import sys
import time
import urllib.request
import zipfile

MIRRORS = [
    "https://mirrors.cloud.tencent.com/pypi/simple",
    "https://repo.huaweicloud.com/repository/pypi/simple",
    "https://mirrors.aliyun.com/pypi/simple",
    "https://mirrors.ustc.edu.cn/pypi/simple",
    "https://pypi.tuna.tsinghua.edu.cn/simple",
    "https://pypi.org/simple",
]

CTX = ssl.create_default_context()
_LINK_RE = re.compile(r'<a\s+[^>]*href="([^"]+)"[^>]*>([^<]+)</a>')


def _get(url, tries=4, timeout=120):
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "pip/26.2"})
            return urllib.request.urlopen(req, timeout=timeout, context=CTX).read()
        except Exception as exc:                  # noqa: BLE001 - retried below
            last = exc
            time.sleep(0.7 * (i + 1))
    raise last


def norm(name):
    return re.sub(r"[-_.]+", "-", name).lower()


def _python_tag():
    return "cp%d%d" % sys.version_info[:2]


def _rank(filename):
    """Preference for a wheel filename on this interpreter and platform.

    Pure-Python wheels are usable everywhere; compiled ones need a matching
    ABI, and a CPython-specific build beats an ``abi3`` one only when both
    match the running interpreter.
    """
    tag = _python_tag()
    win = sys.platform.startswith("win")
    plat = "win_amd64" if win else ("macosx" if sys.platform == "darwin" else "manylinux")
    fn = filename
    if tag in fn and plat in fn:
        return 100
    if "abi3" in fn and plat in fn:
        return 90
    if "py3-none-any" in fn or "py2.py3-none-any" in fn:
        return 80
    if "none-any" in fn:
        return 70
    if plat in fn:
        return 60
    return 0


def _version_key(version):
    return [int(x) if x.isdigit() else -1 for x in re.split(r"[.\-+]", version)[:3]]


def _abs_url(base, href):
    if href.startswith("http"):
        return href
    root = base.split("/simple/")[0].rstrip("/")
    if href.startswith("../../"):
        return root + "/" + href[6:]
    return base + href.lstrip("./")


def _index_page(mirror, package):
    """``(base, [(href, filename)])`` from a PEP 503 index page.

    The filename comes from the *link text*, not from the href: mirrors emit
    ``<a href="../../packages/ab/cd/x.whl#sha256=...">x.whl</a>``, so the href
    does not contain the name at all and a regex over it matches nothing.
    """
    base = "%s/%s/" % (mirror.rstrip("/"), package)
    html = _get(base, timeout=40).decode("utf-8", "replace")
    return base, [(m.group(1), m.group(2).strip()) for m in _LINK_RE.finditer(html)]


def candidates(package):
    """Every installable wheel for ``package``, across mirrors."""
    out = []
    errors = []
    for mirror in MIRRORS:
        try:
            base, links = _index_page(mirror, package)
        except Exception as exc:                  # noqa: BLE001 - try the next mirror
            errors.append("%s: %s" % (mirror, exc))
            continue
        for href, fn in links:
            if not fn.endswith(".whl"):
                continue
            parts = fn[:-4].split("-")
            if len(parts) < 5:
                continue
            out.append({"filename": fn, "url": _abs_url(base, href),
                        "version": parts[1], "mirror": mirror})
        if out:
            break
    if not out and errors:
        raise RuntimeError("no index reachable for %s (%s)" % (package, "; ".join(errors)))
    return out


def pick(package, version=None):
    files = [f for f in candidates(package) if _rank(f["filename"]) > 0]
    if not files:
        return None
    if version:
        exact = [f for f in files if f["version"] == version]
        files = exact or files
    files.sort(key=lambda f: (_rank(f["filename"]), _version_key(f["version"])),
               reverse=True)
    return files[0]


def _metadata(zf):
    for name in zf.namelist():
        if name.endswith(".dist-info/METADATA"):
            return zf.read(name).decode("utf-8", "replace")
    return ""


def _requirements(metadata_text):
    """Parse ``Requires-Dist`` honouring the base (no-extra) environment."""
    try:
        from packaging.requirements import Requirement
    except ImportError:
        return []
    out = []
    for line in metadata_text.splitlines():
        if not line.startswith("Requires-Dist:"):
            continue
        raw = line.split(":", 1)[1].strip()
        try:
            req = Requirement(raw)
        except Exception:                         # noqa: BLE001 - ignore junk
            continue
        if req.marker is not None and not req.marker.evaluate({"extra": ""}):
            continue
        out.append("%s==%s" % (req.name, req.specifier) if str(req.specifier).startswith("==")
                   else req.name)
    return out


def install(dest, packages, log=None):
    """Install ``packages`` (``name`` or ``name==version``) into ``dest``.

    Returns ``(installed, failed)`` where ``installed`` is a list of
    ``name==version`` strings.
    """
    say = log or (lambda _msg: None)
    os.makedirs(dest, exist_ok=True)
    present = {norm(p) for p in os.listdir(dest)
               if os.path.isdir(os.path.join(dest, p))}
    queue = list(packages)
    installed, failed = [], []

    while queue:
        spec = queue.pop(0)
        version = None
        name = spec
        if "==" in spec:
            name, version = spec.split("==", 1)
        key = norm(name)
        if key in present and not version:
            say("%s already present" % key)
            continue

        wheel = pick(name, version)
        if wheel is None:
            failed.append("%s (no compatible wheel)" % spec)
            say("no compatible wheel for %s" % spec)
            continue

        t0 = time.time()
        data = _get(wheel["url"])
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            zf.extractall(dest)
            meta_text = _metadata(zf)

        present.add(key)
        installed.append("%s==%s" % (key, wheel["version"]))
        say("%s %d KB %.1fs" % (wheel["filename"], len(data) // 1024,
                                time.time() - t0))
        queue.extend(_requirements(meta_text))

    return installed, failed


def main(argv=None):
    import argparse
    parser = argparse.ArgumentParser(
        prog="examfig.figdeps",
        description="Install figure dependencies into a vendor directory "
                    "without pip.")
    parser.add_argument("packages", nargs="*",
                        help="package[==version] ...  (empty: the defaults)")
    parser.add_argument("--dest", default=None,
                        help="target directory (default: the resolved vendor dir)")
    args = parser.parse_args(argv)

    from . import env
    dest = args.dest or env.vendor_dir()
    if not dest:
        sys.stderr.write("cannot determine a writable vendor directory\n")
        return 1

    packages = args.packages or ["matplotlib", "numpy", "python-docx", "lxml",
                                 "latex2mathml", "rdkit", "schemdraw"]
    installed, failed = install(dest, packages,
                                log=lambda m: sys.stderr.write("  %s\n" % m))
    sys.stdout.write("vendor: %s\n" % dest)
    sys.stdout.write("installed: %s\n" % (", ".join(installed) or "(nothing)"))
    if failed:
        sys.stdout.write("failed: %s\n" % ", ".join(failed))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

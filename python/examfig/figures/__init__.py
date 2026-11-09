# -*- coding: utf-8 -*-
"""Drawing functions, one module per figure family.

Every function follows the same contract:

    draw_xxx(param, ..., out_path) -> {"marks": [...], ...numeric results}

``marks`` is not decorative.  It is the machine-readable claim "these are the
labels I actually painted", consumed by :mod:`examfig.figcheck` to prove the
figure agrees with the question.  Never reconstruct it from the image and
never write it from memory -- the drawing code must register it.

Submodules are imported lazily.  They all pull in numpy and matplotlib, which
are only importable *after* :func:`examfig.env.bootstrap` has put the vendor
directory on ``sys.path``; importing them at package-import time would fail in
exactly the environment this package is built for.
"""
import importlib

_SUBMODULES = ("incline", "circuit", "solid", "plane", "molecule", "optical")

__all__ = list(_SUBMODULES)


def __getattr__(name):
    if name in _SUBMODULES:
        return importlib.import_module("." + name, __name__)
    raise AttributeError("module %r has no attribute %r" % (__name__, name))


def __dir__():
    return sorted(list(globals()) + list(_SUBMODULES))

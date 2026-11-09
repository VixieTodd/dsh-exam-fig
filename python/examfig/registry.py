# -*- coding: utf-8 -*-
"""Figure registry: name -> drawing function, with parameter metadata.

The tool surface is generated from this table, so adding a figure family means
touching one place.  Each entry declares the parameters the drawing function
accepts, which lets the tool validate input and keeps the documentation honest.

Entries hold ``(module, function)`` *strings* rather than the callables
themselves: importing a drawing module pulls in numpy and matplotlib, which are
not importable until :func:`examfig.env.bootstrap` has run.  Resolution is
deferred to :func:`draw`.
"""
import importlib

# name -> (submodule, function, {param: (type, default, description)})
REGISTRY = {
    "quadratic": (
        "plane", "quadratic",
        {
            "a": ("number", 1.0, "quadratic coefficient a"),
            "b": ("number", -2.0, "linear coefficient b"),
            "c": ("number", -3.0, "constant term c"),
        },
    ),
    "triangle": (
        "plane", "triangle",
        {
            "ac": ("number", 3.0, "leg AC (the right angle is at C)"),
            "bc": ("number", 4.0, "leg BC"),
        },
    ),
    "cube": (
        "solid", "cube",
        {
            "a": ("number", 1.0, "edge length"),
            "show_diagonal": ("boolean", True, "highlight body diagonal AC1"),
        },
    ),
    "pyramid": (
        "solid", "pyramid",
        {
            "a": ("number", 1.0, "base edge length"),
            "h": ("number", 1.05, "height"),
        },
    ),
    "incline": (
        "incline", "incline",
        {
            "theta_deg": ("number", 30.0, "angle of inclination in degrees"),
            "G": ("number", 1.55, "weight (arrow length)"),
            "L": ("number", 7.2, "slope length in figure units"),
        },
    ),
    "circuit": (
        "circuit", "circuit",
        {
            "emf": ("number", 6.0, "battery EMF in volts"),
            "r1": ("number", 2.0, "first resistor in ohms"),
            "r2": ("number", 4.0, "second resistor in ohms"),
        },
    ),
    "lens": (
        "optical", "thin_lens",
        {
            "f": ("number", 10.0, "focal length"),
            "u": ("number", 30.0, "object distance"),
            "height": ("number", 6.0, "object height in figure units"),
        },
    ),
    "mirror": (
        "optical", "mirror",
        {
            "f": ("number", 10.0, "focal length"),
            "u": ("number", 30.0, "object distance"),
            "height": ("number", 6.0, "object height in figure units"),
        },
    ),
    "molecule": (
        "molecule", "molecule",
        {
            "smiles_list": ("array", ["CCO"], "SMILES strings, one per structure"),
        },
    ),
}


def names():
    return sorted(REGISTRY)


def parameters(name):
    entry = REGISTRY.get(name)
    if entry is None:
        raise KeyError("unknown figure kind: %r (have: %s)"
                       % (name, ", ".join(names())))
    return entry[2]


def resolve(name):
    """Import and return the drawing callable for ``name``."""
    entry = REGISTRY.get(name)
    if entry is None:
        raise KeyError("unknown figure kind: %r (have: %s)"
                       % (name, ", ".join(names())))
    submodule, function, _meta = entry
    module = importlib.import_module(".figures." + submodule, __package__)
    return getattr(module, function)


def coerce(name, params):
    """Validate and normalise ``params`` for ``name``."""
    entry = REGISTRY.get(name)
    if entry is None:
        raise KeyError("unknown figure kind: %r (have: %s)"
                       % (name, ", ".join(names())))
    meta = entry[2]
    unknown = set(params) - set(meta)
    if unknown:
        raise ValueError("unknown parameter(s) for %r: %s (accepted: %s)"
                         % (name, ", ".join(sorted(unknown)), ", ".join(sorted(meta))))
    kwargs = {}
    for key, (kind, default, _desc) in meta.items():
        value = params.get(key, default)
        if kind == "number":
            kwargs[key] = float(value)
        elif kind == "boolean":
            kwargs[key] = bool(value)
        elif kind == "array":
            kwargs[key] = list(value)
        else:
            kwargs[key] = value
    return kwargs


def draw(name, params, out_path):
    """Call the drawing function for ``name`` with validated ``params``."""
    return resolve(name)(out_path=out_path, **coerce(name, params))


def catalog():
    """Machine-readable description of every figure kind."""
    out = []
    for name in names():
        _sub, _fn, meta = REGISTRY[name]
        out.append({
            "kind": name,
            "parameters": [
                {"name": k, "type": v[0], "default": v[1], "description": v[2]}
                for k, v in meta.items()
            ],
        })
    return out

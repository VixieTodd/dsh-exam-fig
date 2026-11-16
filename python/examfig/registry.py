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
    "trig": (
        "trig", "trig",
        {
            "A": ("number", 1.0, "amplitude A in y = A sin(omega x + phi) + shift"),
            "omega": ("number", 1.0, "angular frequency omega (period = 2pi/|omega|)"),
            "phi": ("number", 0.0, "phase phi in radians"),
            "shift": ("number", 0.0, "vertical shift (midline y)"),
            "periods": ("number", 1.0, "how many periods to show after the first peak"),
        },
    ),
    "power": (
        "power", "power",
        {
            "exponents": ("array", [1.0, 2.0, 3.0, -1.0, 0.5],
                          "exponents a for y = x^a, drawn on one pair of axes"),
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
    # -- math, batch 1 ----------------------------------------------------
    "numberline": (
        "numberline", "numberline",
        {
            "lo": ("number", -4.0, "left end of the axis"),
            "hi": ("number", 6.0, "right end of the axis"),
            "intervals": ("array", [[-1.0, 2.0, "closed"]],
                          "intervals as [a, b, style]; a or b null for an "
                          "unbounded end; style is closed, open, lopen, "
                          "ropen or none"),
            "points": ("array", [], "numbers to mark on the axis"),
        },
    ),
    "venn": (
        "venn", "venn",
        {
            "sets": ("array", ["A", "B"], "set names, two or three of them"),
            "regions": ("object", {},
                        "region key -> text drawn in it; keys are A, B, AB, U "
                        "(two sets) or A, B, C, AB, AC, BC, ABC, U (three)"),
            "shade": ("array", [], "region keys to fill"),
        },
    ),
    "explog": (
        "algebra", "explog",
        {
            "base": ("number", 2.0, "base a of y = a**x and y = log_a x"),
            "show_log": ("boolean", True, "draw the logarithm as well"),
            "show_reciprocal": ("boolean", True,
                                "draw y = (1/a)**x, the y-axis mirror"),
            "span": ("number", 3.4, "half-width of the window in graph units"),
        },
    ),
    "piecewise": (
        "algebra", "piecewise",
        {
            "mode": ("string", "absolute", "absolute (y = |ax+b|+c) or pieces"),
            "abs_a": ("number", 1.0, "a in y = |a x + b| + c"),
            "abs_b": ("number", 0.0, "b in y = |a x + b| + c"),
            "abs_c": ("number", 0.0, "c in y = |a x + b| + c"),
            "knots": ("array", [[-3.0, -1.0], [-1.0, 1.0], [1.0, -2.0]],
                      "pieces mode: [x, y] vertices joined by straight segments"),
        },
    ),
    "unitcircle": (
        "unitcircle", "unitcircle",
        {
            "theta_deg": ("number", 50.0, "angle of the terminal side, degrees"),
            "show_tan": ("boolean", True, "draw the tangent segment AT"),
            "show_angles": ("boolean", True, "label the angle arc"),
        },
    ),
    "solve_triangle": (
        "geometry", "triangle_solve",
        {
            "a": ("number", 5.0, "side a, opposite vertex A"),
            "b": ("number", 6.0, "side b, opposite vertex B"),
            "c": ("number", 7.0, "side c, opposite vertex C"),
            "show_circle": ("boolean", True, "draw the circumcircle and R"),
            "show_angles": ("boolean", True, "mark each angle with its value"),
        },
    ),
    "circleline": (
        "geometry", "circle_line",
        {
            "r": ("number", 3.0, "circle radius"),
            "dist": ("number", 1.8, "distance from the centre to the line"),
            "angle_deg": ("number", 0.0, "direction of the line, degrees"),
            "tangent": ("boolean", False,
                        "force dist = r, making the line a tangent"),
        },
    ),
    "vectors": (
        "geometry", "vectors",
        {
            "u": ("array", [3.0, 1.0], "first vector [x, y]"),
            "v": ("array", [1.0, 2.5], "second vector [x, y]"),
            "mode": ("string", "both",
                     "both, parallelogram or triangle"),
        },
    ),
    # -- physics, batch 1 -------------------------------------------------
    "motion": (
        "kinematics", "motion",
        {
            "x0": ("number", 0.0, "initial position"),
            "v0": ("number", 6.0, "initial velocity"),
            "a": ("number", -2.0, "acceleration"),
            "t_end": ("number", 0.0,
                      "last time shown; 0 picks a window around the turning point"),
            "show_area": ("boolean", True,
                          "shade the area under v-t, which equals the displacement"),
        },
    ),
    "wave": (
        "waves", "wave",
        {
            "amplitude": ("number", 2.0, "amplitude A"),
            "wavelength": ("number", 4.0, "wavelength lambda"),
            "cycles": ("number", 2.0, "how many wavelengths to show"),
            "speed": ("number", 0.0,
                      "wave speed; when given, the period is returned (not painted)"),
        },
    ),
    "vibration": (
        "waves", "vibration",
        {
            "amplitude": ("number", 2.0, "amplitude A"),
            "period": ("number", 0.8, "period T"),
            "cycles": ("number", 2.5, "how many periods to show"),
        },
    ),
    "standingwave": (
        "waves", "standing",
        {
            "amplitude": ("number", 2.0, "amplitude A"),
            "length": ("number", 6.0, "length L between the two fixed ends"),
            "antinodes": ("number", 3,
                          "half-wavelengths fitting between the ends (harmonic n)"),
            "show_envelope": ("boolean", True,
                              "dashed envelope through the antinodes"),
        },
    ),
    "refraction": (
        "optics2", "refraction",
        {
            "n1": ("number", 1.0, "refractive index the incident ray comes from"),
            "n2": ("number", 1.5, "refractive index beyond the interface"),
            "incidence_deg": ("number", 45.0, "angle of incidence from the normal"),
            "show_critical": ("boolean", True,
                              "draw the critical ray when n1 > n2"),
        },
    ),
    "doubleslit": (
        "optics2", "doubleslit",
        {
            "wavelength": ("number", 600.0, "wavelength in nanometres"),
            "slit_separation": ("number", 0.2, "slit separation d in millimetres"),
            "distance": ("number", 1.0, "slit-to-screen distance L in metres"),
            "window_mm": ("number", 20.0, "width of screen shown, millimetres"),
            "n_fringes": ("number", 9, "how many orders to number"),
        },
    ),
    "energylevel": (
        "optics2", "energylevel",
        {
            "z": ("number", 1.0, "atomic number Z (1 for hydrogen)"),
            "n_max": ("number", 4, "highest level drawn"),
            "transitions": ("array", [[3, 1], [2, 1]],
                            "transitions as [n_hi, n_lo] pairs"),
        },
    ),
    "pv": (
        "thermo", "pv",
        {
            "states": ("array", [3.0, 1.0],
                       "starting state as [p, V]"),
            "processes": ("array",
                          [["isobar", 3.0], ["isochore", 1.0],
                           ["isobar", 1.0], ["isochore", 3.0]],
                          "steps as [kind, target]; kind is isobar, isochore, "
                          "isotherm or adiabat"),
            "show_area": ("boolean", True, "shade the enclosed area"),
        },
    ),
    # -- maths, batch 2 ----------------------------------------------------
    "conic": (
        "conic", "conic",
        {
            "kind": ("string", "ellipse", "ellipse, hyperbola or parabola"),
            "a": ("number", 3.0, "semi-axis a (ignored by the parabola)"),
            "b": ("number", 2.0, "semi-axis b (ignored by the parabola)"),
            "p": ("number", 2.0,
                  "focal parameter of y^2 = 2 p x (parabola only)"),
            "show_directrix": ("boolean", True, "draw the directrix"),
            "show_asymptotes": ("boolean", True, "draw the asymptotes"),
        },
    ),
    "histogram": (
        "stats", "histogram",
        {
            "samples": ("array", [],
                        "the raw sample values; binning happens here, so the "
                        "bar heights and the axis cannot disagree"),
            "bins": ("number", 6, "number of equal-width classes"),
            "show_polygon": ("boolean", True, "draw the frequency polygon"),
            "show_normal": ("boolean", True,
                            "overlay the fitted normal curve, mean and s"),
            "xlabel": ("string", "数据", "x axis label"),
            "ylabel": ("string", "频率/组距", "y axis label"),
        },
    ),
    "scatter": (
        "stats", "scatter",
        {
            "points": ("array", [],
                       "the sample as [[x, y], ...]; the fit is computed from it"),
            "slope": ("number", 0.0, "unused when show_fit computes the fit"),
            "intercept": ("number", 0.0, "unused when show_fit computes the fit"),
            "show_fit": ("boolean", True, "draw the least-squares line and r"),
            "xlabel": ("string", "$x$", "x axis label"),
            "ylabel": ("string", "$y$", "y axis label"),
        },
    ),
    "forces": (
        "mechanics", "forces",
        {
            "magnitudes": ("array", [],
                           "force magnitudes in N; arrow lengths share one scale"),
            "angles": ("array", [],
                       "direction of each force in degrees from +x, one per "
                       "magnitude"),
            "weight": ("number", 0.0, "adds gravity straight down, in N"),
            "incline_deg": ("number", 0.0,
                            "tilt of the surface; the decomposition axes "
                            "rotate with it"),
            "show_decomposition": ("boolean", True,
                                   "draw F_parallel and F_perpendicular"),
        },
    ),
    "projectile": (
        "mechanics", "projectile",
        {
            "speed": ("number", 10.0, "launch speed v0, m/s"),
            "angle_deg": ("number", 45.0,
                          "launch angle above the horizontal; 0 is a "
                          "horizontal throw"),
            "launch_height": ("number", 0.0, "launch height above the ground"),
            "gravity": ("number", 9.8, "g in m/s^2"),
            "show_components": ("boolean", True,
                                "draw v0 and its vx, vy components"),
            "show_range": ("boolean", True, "mark the range on the ground"),
        },
    ),
    "circular": (
        "mechanics", "circular",
        {
            "radius": ("number", 2.0, "loop radius r, m"),
            "speed": ("number", 4.0, "speed at the point shown, m/s"),
            "mass": ("number", 0.5, "mass m, kg"),
            "angle_deg": ("number", 35.0,
                          "where the body sits, degrees from the top"),
            "show_critical": ("boolean", True,
                              "mark v_c = sqrt(g r) and the verdict"),
            "show_forces": ("boolean", True, "draw mg and N at the body"),
        },
    ),
    "fieldlines": (
        "em", "fieldlines",
        {
            "charges": ("array", [],
                        "point charges as [[x, y, q], ...]; the default is a "
                        "dipole"),
            "n_lines": ("number", 12, "how many field lines to seed"),
            "n_equi": ("number", 6, "equipotential pairs to draw"),
            "extent": ("number", 3.2, "half-width of the field region"),
            "show_labels": ("boolean", True,
                            "label the charges and add the legend"),
        },
    ),
    "magnetic": (
        "em", "magnetic",
        {
            "charge": ("number", 1.0, "magnitude of the charge, C"),
            "speed": ("number", 1.0, "speed v, m/s"),
            "mass": ("number", 1.0, "mass m, kg"),
            "field": ("number", 1.0, "flux density B, T"),
            "sign": ("number", 1,
                     "+1 for a positive charge, -1 for negative"),
            "field_mode": ("string", "in",
                           "in: field into the page, out: out of it"),
            "angle_deg": ("number", 90.0,
                          "angle between v and B; 90 gives a circle"),
        },
    ),
    "induction": (
        "em", "induction",
        {
            "rod_length": ("number", 1.0, "length L of the rod, m"),
            "speed": ("number", 2.0, "speed v of the rod, m/s"),
            "field": ("number", 0.5, "flux density B, T"),
            "resistance": ("number", 2.0, "total circuit resistance, ohm"),
            "rail_length": ("number", 3.0, "length of the rails"),
            "field_mode": ("string", "in",
                           "in: field into the page, out: out of it"),
        },
    ),
    "circuit2": (
        "circuit2", "circuit2",
        {
            "emf": ("number", 6.0, "supply emf, V"),
            "r1": ("number", 2.0, "resistance of the first branch, ohm"),
            "r2": ("number", 3.0, "fixed resistance in the second branch"),
            "rheostat": ("number", 4.0,
                         "sliding resistance as drawn; a 20 ohm rheostat at "
                         "midpoint passes 10"),
            "show_ammeter": ("boolean", True,
                             "ammeter in the main line (total current)"),
            "show_voltmeter": ("boolean", True,
                               "voltmeter across the parallel group"),
        },
    ),
    # -- chemistry ---------------------------------------------------------
    "titration": (
        "chemistry", "titration",
        {
            "analyte_conc": ("number", 0.1, "concentration of the analyte, mol/L"),
            "analyte_volume": ("number", 20.0, "volume of the analyte, mL"),
            "titrant_conc": ("number", 0.1, "concentration of the titrant, mol/L"),
            "ka": ("number", 1.8e-5,
                   "Ka of the acid (or Kb of the base); >= 1 means strong"),
            "mode": ("string", "acid", "acid (titrated with base) or base"),
            "show_half": ("boolean", True,
                          "mark the half-equivalence point and pKa"),
        },
    ),
    "equilibrium": (
        "chemistry", "equilibrium",
        {
            "v_f0": ("number", 1.0, "initial forward rate"),
            "v_r0": ("number", 0.2, "initial reverse rate"),
            "v_eq": ("number", 0.0,
                     "first equilibrium rate; 0 uses the mean of the two starts"),
            "t_change": ("number", 3.0, "when the condition changes"),
            "jump_f": ("number", 0.6, "instant change in the forward rate"),
            "jump_r": ("number", 0.0, "instant change in the reverse rate"),
            "tau": ("number", 0.55, "relaxation time"),
            "t_end": ("number", 8.0, "end of the time axis"),
            "show_shift": ("boolean", True, "mark the shift and the new equilibrium"),
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
        elif kind == "object":
            # A mapping parameter (region -> label) must not go through
            # ``list()``: that yields the keys and silently drops every value.
            if not isinstance(value, dict):
                raise ValueError(
                    "parameter %r of %r takes an object, got %s"
                    % (key, name, type(value).__name__))
            kwargs[key] = dict(value)
        elif kind == "string":
            kwargs[key] = str(value)
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

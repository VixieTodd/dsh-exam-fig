# dsh-exam-fig

Figures for exam questions — math, physics, chemistry — drawn **from the
numbers in the question**, plus a checker that proves the picture agrees with
the prose.

A DSH host plugin: four tools, no UI, no client half.

```
exam_figure          draw one figure from parameters
exam_figure_catalog  what can be drawn, and with which parameters
exam_figure_check    does the figure show everything the stem claims?
exam_figure_doctor   is this install usable?
```

---

## Why this exists

Asking a model to "draw a 30° inclined plane with a 2 kg block" produces a
picture that *looks* right and is often wrong: the component arrows drawn at
full length instead of `G sin θ`, the right angle on the wrong vertex, `R₂`
labelled where `R₁` belongs, a concave mirror drawn with its image behind the
glass. Every one of those is a silent error — the page still renders.

The fix is not a better prompt. It is to stop treating the figure as an
illustration and treat it as **a derived artefact of the question's numbers**:

1. **Parameters in, numbers out.** `incline(theta_deg=30, G=1.55)` computes
   `G∥ = G sin 30°` itself. The arrow is drawn at that length because that is
   the length it is; there is no separate "draw an arrow about this long" step
   that can disagree with the answer.
2. **The drawing reports what it painted.** Each function returns
   `marks`: the labels it actually placed. `figcheck` compares that against
   what the question stem requires. A mislabelled vertex fails, even though
   the image looks fine.
3. **Geometry that lies gets caught by arithmetic, not by eye.** `figcheck`
   was written after it caught a `Rt△ABC` whose right angle had been drawn on
   vertex A while the stem said `∠C = 90°`.

---

## Quick start

### 1. Install the plugin

```bash
dsh plugin install /absolute/path/to/dsh-exam-fig
```

or, inside a session:

```
plugin_manager  action=install_bundle  target=/absolute/path/to/dsh-exam-fig
```

The bundle is host-only: `index.js` + `cordis.patch.yml` + `package.json`. It
shells out to Python, so the next step matters.

### 2. Provide the Python dependencies

The plugin does **not** bundle wheels — they are ~200 MB and version-specific.
Fetch them once into a vendor directory:

```bash
cd /path/to/dsh-exam-fig
python -m examfig.figdeps
```

That reads a PyPI mirror, resolves `Requires-Dist` by hand, and unpacks wheels
into `python/vendor/`. It deliberately does not use `pip` — see
[Why not pip](#why-not-pip).

Check it worked:

```bash
python -m examfig.cli doctor
```

```json
{"ok": true, "python": "3.12.14", "font": "Microsoft YaHei",
 "omml": true, "missing": [],
 "packages": {"matplotlib": "3.11.2", "numpy": "2.5.4", "rdkit": "2026.9.1", ...}}
```

Then from the agent side, `exam_figure_doctor` reports the same thing.

### 3. Draw something

```
exam_figure(kind="incline", params={"theta_deg": 30, "G": 1.55})
```

```json
{"ok": true, "kind": "incline", "path": ".../examfig/incline.png",
 "marks": ["30", "G", "Gperp", "Gpar"],
 "detail": {"G_par": 0.775, "G_perp": 1.342, "ratio": 0.5773502691896257}}
```

### 4. Prove it agrees with the question

```
exam_figure_check(
  specs=[{no: 1, need: ["G", "G_par", "G_perp", "30"], text: "如图1，物块重 G"}],
  figures={1: {marks: ["G", "Gpar", "Gperp", "30"]}})
```

```
ALL PASS
PASS [图 1] 4 项标注一致
```

Point it at a figure that is missing a mark and it fails, naming the mark.

---

## Environment

| Requirement | Notes |
| --- | --- |
| **DSH** | `^0.2.2-rc.1`. Host-only bundle; needs the `tools` and `subprocess` services. |
| **Node** | ≥ 20 (the plugin itself uses only `node:` builtins). |
| **Python** | 3.10+. By default the interpreter DSH ships (`$DSH_HOME/dsh-runtimes/.../python`); override with `DSH_EXAMFIG_PYTHON`. |
| **CJK font** | Any of Microsoft YaHei, SimHei, Noto Sans CJK SC, PingFang SC, WenQuanYi Zen Hei… Chinese labels become boxes without one. `exam_figure_doctor` reports the choice. |
| **Microsoft Office** *(optional)* | Supplies `MML2OMML.XSL`, needed only for native Word equations. Without it, equations degrade to plain text. Override the path with `DSH_EXAMFIG_MML2OMML`. |

Platforms: Windows is what it was developed and tested on. Nothing is
Windows-specific except the default font list and the Office path probe;
macOS/Linux should work once a CJK font is present.

### Environment variables

| Variable | Purpose |
| --- | --- |
| `DSH_EXAMFIG_PYTHON` | Interpreter to spawn |
| `DSH_EXAMFIG_VENDOR` | Directory holding the unpacked wheels |
| `DSH_EXAMFIG_CACHE` | matplotlib's `MPLCONFIGDIR` |
| `DSH_EXAMFIG_MML2OMML` | Path to `MML2OMML.XSL` |

---

## Architecture

```
dsh-exam-fig/
├── index.js              the plugin: four tools, spawns Python
├── cordis.patch.yml      bundle patch (one insert)
├── package.json
├── python/examfig/
│   ├── cli.py            one JSON object per subcommand — the seam
│   ├── env.py            sys.path bootstrap, matplotlib cache, CJK font probe
│   ├── registry.py       kind -> (module, function, params)  [lazy]
│   ├── figcheck.py       declared labels vs painted marks
│   ├── figures/
│   │   ├── plane.py      quadratic, triangle
│   │   ├── power.py      y = x^a family on one pair of axes
│   │   ├── solid.py      cube, pyramid (orthographic + back-face culling)
│   │   ├── incline.py    inclined plane with resolved components
│   │   ├── circuit.py    series circuit (schemdraw)
│   │   ├── optical.py    thin lens, concave mirror
│   │   └── molecule.py   skeletal structures (RDKit)
│   ├── docxkit.py        python-docx helpers: fonts, figure sizing, mixed runs
│   ├── omml.py           LaTeX -> native Word equation
│   ├── chem.py           formulae with real subscripts; = vs -> per convention
│   └── figdeps.py        wheel fetcher (no pip)
└── tests/
    ├── smoke.mjs         tool definitions, render, output schemas
    └── test_engine.py    the drawing maths, the checker, the chemistry
```

### The seam: one JSON object per call

Node never imports Python and Python never knows Node exists. `index.js` spawns
`python -m examfig.cli <subcommand>` and parses the **last line** of stdout as a
single JSON object; everything else goes to stderr. A failing child therefore
still returns a machine-readable `{ok: false, error: ...}` instead of a
traceback the caller would have to scrape.

Output is collected in `{ maxBytes }` mode, which means `handle.stdout` is
`undefined` and the bytes are read from
`handle.collected.stdout.readFrom(0)` **after** `done` resolves. Attaching a
`data` listener there throws.

### Lazy imports are structural, not stylistic

`python/vendor/` is only on `sys.path` after `env.bootstrap()` runs. So
`figures/__init__.py` exposes its submodules through a PEP 562 `__getattr__`,
and `registry.REGISTRY` stores `(module_string, function_string)` pairs rather
than callables. Importing a drawing module at package-import time fails with
`ModuleNotFoundError: numpy` in exactly the environment this ships for.

### Two ways of placing a label

`labelplace.py` solves "where does this point annotation go" as a small
optimisation: 8 directions × 2 distances, cost = out-of-frame + overlap with
other labels + crossing a line + distance from its anchor. It needs a real
renderer measurement (`text.get_window_extent`) to know how big a label is —
estimating from character count is wrong by 2× once Chinese and mathtext
subscripts are involved.

It is the wrong tool for a label that belongs to a *whole component*. In a
circuit diagram the label belongs outside the loop, near the middle of the
symbol; running the optimiser there puts `R₂` inside the loop, which is simply
wrong on a schematic. So `circuit.py` places labels deterministically: component
midpoint + outward normal × measured offset. **Ask what the label is anchored
to before choosing a placement strategy.**

### Collision audit: the last thing that runs before saving

`labelplace.py` decides where a label goes. `layout.py` asks a different
question afterwards: **is the finished picture actually readable?** Placement
is decided one label at a time and cannot see what the last label did to the
first, or that a label ended up on a curve or half outside the canvas.

Every figure now ends with `layout.finish(fig, ax, path)` instead of
`fig.savefig(...)`. It measures every text box, reports three kinds of
collision, tries to nudge the offenders apart, saves, and returns:

```json
{"collisions": 0, "fixed": 2, "remaining": []}
```

That report travels back through the tool layer, and `exam_figure` prints it:

```
layout: clean (2 label(s) nudged apart)
```

or, when a repair fails:

```
layout: 1 UNRESOLVED COLLISION(S)
  - overlap: "G" vs "G_{\perp}"
```

**Unresolved collisions are reported, never hidden.** A figure that cannot be
fixed is still written to disk — the caller needs to see it — but the report
says so, because a silently mislabelled figure is exactly the failure this
project exists to prevent.

Three severities, because they are not equally bad:

| Severity | Meaning | Weight |
| --- | --- | --- |
| `overlap` | two labels on top of each other — both unreadable | 10 |
| `frame` | a label outside the axes limits (and `bbox_inches="tight"` will stretch the page to fit it) | 6 |
| `line` | a label sitting on a drawn stroke, or on the block outline | 1 |

The repair tries 17 candidate displacements (multiples of the label's own
width/height) and accepts one only if it strictly lowers that label's score.
Anything else leaves the label exactly where it was.

#### The `skip` list, and why it exists

Some labels are *supposed* to touch what they describe: an angle mark sits in
the wedge between its two rays, `O` sits in the angle between the axes, `x` and
`y` sit at the ends of the axes they name. Auditing those as collisions and
"fixing" them pushed the incline's `30°` label outside the figure — a real
regression, caught by looking at the output rather than at the report.

So `finish(..., skip=(...))` exempts named labels from the line and frame
checks. **They are still checked for overlap**, because two pieces of text on
top of each other are wrong under any convention.

```python
report = layout.finish(fig, ax, out_path, skip=("$O$", "$x$", "$y$"))
```

#### Two things the audit must not mistake for obstacles

* **An empty annotation is an arrow.** `ax.annotate("", ...)` creates a `Text`
  with no string; treating it as a label would report every arrowhead.
* **A marker-only plot is a dot, not a stroke.** `ax.plot(x, y, "k.", ms=3.5)`
  draws the vertex dot; counting it as a line would push every vertex label off
  its vertex.

### What the layout pass does *not* do

It does not replace thinking about the figure. Three arrows from one origin,
30° apart, cannot be labelled by any automatic pass — the labels have to go
somewhere, and "somewhere" is decided by the geometry. The fix there was to
change the *drawing*: shorter arrows, a flatter ramp, so the labels have room.
See `figures/incline.py`.

It also does not touch `molecule`: RDKit lays out structures and their atom
labels itself, with no matplotlib axes to measure. That kind reports
`{"applicable": false}` so a caller iterating over all ten does not have to
special-case it.

---

## The four tools

### `exam_figure`

| Parameter | Type | Meaning |
| --- | --- | --- |
| `kind` | string | one of the ten kinds |
| `params` | object | that kind's parameters; unknown keys are refused |
| `out` | string | output PNG; defaults to `<cwd>/examfig/<kind>.png` |

Returns `{ok, kind, path, bytes, marks, detail}`. `marks` is the label list the
drawing function registered as it painted — never reconstructed from the image.

### `exam_figure_catalog`

Ten kinds with each parameter's type and default. Call this instead of
guessing a parameter name; `coerce()` rejects unknown keys and lists the
accepted ones.

| kind | parameters |
| --- | --- |
| `quadratic` | `a`, `b`, `c` |
| `power` | `exponents` (list, default `[1, 2, 3, -1, 1/2]`) |
| `triangle` | `ac`, `bc` (right angle at C) |
| `cube` | `a`, `show_diagonal` |
| `pyramid` | `a`, `h` |
| `incline` | `theta_deg`, `G`, `L` |
| `circuit` | `emf`, `r1`, `r2` |
| `lens` | `f`, `u`, `height` |
| `mirror` | `f`, `u`, `height` |
| `molecule` | `smiles_list` |

### `exam_figure_check`

```
specs:   [{no, need: [labels], text: stem}]
figures: {no: {marks: [...]}}
```

Fails when a required label is absent, or when a stem says `如图 7` and figure 7
was never drawn. Extra marks only warn.

Normalisation folds `G_∥`, `G_{\parallel}`, `G∥` onto one key. Substring match
in either direction, because the figure writes `R_1=2 Ω` where the stem only
promised `R_1`. **Except for single-character symbols**, which must match
exactly — `G` is a substring of `Gperp`, and treating that as a match was a real
false pass.

### `exam_figure_doctor`

Interpreter, resolved vendor directory, chosen CJK font, package versions,
whether OMML is available. `ok: false` comes with a `hint` naming the command
to run.

---

## Building a paper

The plugin draws figures; assembling a `.docx` is the Python side's job too.
`docxkit.py` carries the layout rules that cost render cycles to learn:

* **Left-align Chinese paragraphs.** Word's default justified alignment
  stretches short lines glyph by glyph: a four-word answer line rendered as
  `顶 点 纵 坐 标`.
* **Size figures by aspect ratio.** A fixed width makes a wide circuit 2.7 cm
  tall and a tall triangle 6.9 cm tall. Target a height, compute the width,
  clamp it.
* **Bind figures to their captions** with `keep_with_next`, so Word does not
  strand the picture on one page and its caption on the next.

Equations go in as **native Word OMML**, not images: `latex2mathml` →
`MML2OMML.XSL` → element appended to the paragraph. Chinese inside an equation
(the condition above a reaction arrow) needs `w:rFonts` patched onto those
runs, or Cambria Math renders tofu.

Chemical formulae go in as **plain runs with `font.subscript`**, not OMML.
LibreOffice ignores `m:sty m:val="p"` when importing OMML and italicises `H₂O`;
a subscript run is understood everywhere. Inorganic equations use `=`, organic
use `→`, with the condition written between the two halves (`=点燃=`,
`→点燃→`) — the Chinese textbook convention.

---

## Verification

```bash
# tool layer: definitions, render, output schemas (no Python needed)
node tests/smoke.mjs

# engine: the drawing maths, the checker, the chemistry
python tests/test_engine.py
```

Both are dependency-free — no pytest, no test framework. They assert on the
**numbers the drawing functions return**, not on pixels. A pixel comparison
passes on a beautifully drawn wrong figure, which is the whole failure mode
this project exists to prevent.

---

## Why not pip

On a sandboxed DSH install `pip` cannot work, and the reason is not network or
permissions on the target directory:

* `pip` downloads into `tempfile.mkdtemp()` and then writes the wheel inside
  that directory. The file sandbox allows creating the directory and **denies
  writing a file into it** — `PermissionError: [Errno 13]`, regardless of
  network.
* `site-packages` is equally unwritable, so a `.pth` shim is not an option.

`figdeps.py` sidesteps all of it: read the simple index from a mirror, resolve
`Requires-Dist` by hand, `zipfile.extractall` into a plain directory that
`env.bootstrap()` prepends to `sys.path`.

Mirrors are tried in order, PyPI's CDN last — from mainland China it drops long
transfers with `SSL: UNEXPECTED_EOF_WHILE_READING` often enough that a 9 MB
wheel never completes.

Note that a mirror's index page puts the filename in the **link text**, not the
href: `<a href="../../packages/ab/cd/hash.whl#sha256=…">name-1.0.whl</a>`. A
regex over the href matches nothing.

Two more sandbox constraints worth knowing:

* `MPLCONFIGDIR` must point somewhere writable, or matplotlib's teardown throws
  `PermissionError` into stderr on every run.
* A PNG cannot be written into a freshly `mkdtemp()`'d directory, so tests
  write into a scratch folder beside themselves instead.

---

## Licence

MIT — see [LICENSE](LICENSE). Dependency licences are all permissive
(BSD / MIT / Apache-2.0) and listed in [THIRD-PARTY.md](THIRD-PARTY.md).
No third-party code is vendored in this repository.

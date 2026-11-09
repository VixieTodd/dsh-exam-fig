# Writing an exam paper with `dsh-exam-fig`

A worked walkthrough: three questions, one per subject, from parameters to a
rendered `.docx` that survives LibreOffice. Every trap below was hit for real.

---

## The shape of the job

A question with a figure has **one source of truth: the parameters**.

```
parameters ──> figure function ──> PNG + marks
     │                                 │
     └──> stem text (numbers)          │
                    │                  │
                    └──> figcheck <────┘
                              │
                        PASS / FAIL
```

If the stem says 30° and the parameters say 30°, both agree by construction.
If someone edits one and not the other, `figcheck` catches it. The figure is
never drawn "to match" a sentence — it is drawn from the same numbers the
sentence was written from.

---

## 1. Math: a quadratic

```python
from examfig import registry

result = registry.draw("quadratic", {"a": 1, "b": -2, "c": -3}, "figs/q1.png")
# {"vertex": (1.0, -4.0), "roots": [-1.0, 3.0],
#  "marks": {"O", "x", "y", "1", "-4", "-1", "3"}}
```

The stem is then written from the **same numbers**, never by reading the
picture:

> 如图 1，二次函数 `y = x² - 2x - 3` 的图象与 x 轴交于 A(-1, 0)、B(3, 0)，
> 顶点为 P(1, -4)。

`figcheck` compares `need = {O, x, y, 1, -4, -1, 3}` against the returned
`marks`. Note that the vertex label `(1, -4)` is *two* marks — the x-coordinate
and the y-coordinate are separate labels on the drawing, and the checker folds
them by containment.

### What goes wrong

* **Roots outside the frame.** The default window is `vx ± 2.9`; a parabola
  with roots at -4 and 6 silently clips. The draw function widens the window to
  cover the roots — this is a real fix, not a convenience.
* **Root labels under the curve.** Placing them "below the axis" is not
  enough: the descending branch sweeps exactly through that region. They must
  also move *away from the vertex*.

---

## 2. Physics: the inclined plane

```python
result = registry.draw("incline", {"theta_deg": 30, "G": 1.55}, "figs/p1.png")
# {"G_par": 0.775, "G_perp": 1.342, "ratio": 0.5773502691896257,
#  "marks": {"G", "Gpar", "Gperp", "30"}}
```

`ratio == tan(30°)` is asserted inside the module. That single assertion is
worth more than any amount of visual inspection: the classic error is drawing
`G∥` and `G⊥` at full length, which looks plausible and teaches the student a
falsehood.

### What goes wrong

* **`n_out` must be orthogonal to the slope.** The first version used
  `(-sin θ, cos θ)`; its dot product with the slope direction is
  `2 sin θ cos θ`, not zero. The block was drawn as a parallelogram and `G⊥`
  pointed off the surface. The module now asserts
  `abs(n_out @ up_slope) < 1e-9`.
* **The angle belongs at the lower-right vertex**, between the ground and the
  ramp — not at the origin. Textbooks are consistent about this.
* **Three arrows share one origin.** `G`, `G∥` and `G⊥` all start at the block's
  centre, 30° apart. Labels cannot be resolved by a placement optimiser alone;
  the winning move was to change the **geometry** — shorter arrows, a flatter
  ramp — so the labels have somewhere to go.

```python
# the assertion that keeps this honest
assert abs(n_out @ up_slope) < 1e-9
```

---

## 3. Chemistry: a molecular structure and an equation

```python
result = registry.draw("molecule", {"smiles_list": ["CCO", "CC(=O)O"]}, "figs/c1.png")
# {"formulas": ["C2H6O", "C2H4O2"], "marks": {"C2H6O", "C2H4O2"}}
```

The formula is computed by RDKit (`CalcMolFormula`), not typed by hand — so the
`C2H6O` in the stem and the structure in the picture cannot disagree.

For the equation, use `chem.equation_parts`:

```python
from examfig import chem
parts = chem.equation_parts("C2H5OH + 3O2", "2CO2 + 3H2O",
                            condition="点燃", organic=True)
# [("c", [("C",False),("2",True),("H",False),...]), ("t", " →点燃→ "), ...]
```

### What goes wrong

* **Organic vs inorganic.** `=` for inorganic, `→` for organic. Passing
  `organic=False` on an organic reaction is a chemistry error the checker
  cannot see; get it right in the call.
* **Coefficients are not subscripts.** `2H2 + O2` has three digits: the leading
  `2` is a coefficient (full size), the other two are subscripts. The rule is
  `is_sub = (previous token is an element symbol or ")") and (not part of a
  multi-digit count)`.
* **OMML renders chemical formulae as italics.** Even with correct
  `m:sty m:val="p"`, LibreOffice ignores it. Use plain runs with
  `font.subscript = True` instead — see `chem.py`'s module docstring.

---

## 4. Assembling the document

`docxkit.py` is where the layout rules live. Three of them are non-negotiable:

```python
from examfig import docxkit

# 1. left-align Chinese prose
p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.LEFT
p.paragraph_format.first_line_indent = Cm(0)

# 2. size figures by aspect ratio, not a fixed width
docxkit.add_picture(doc, path)      # targets 4.3 cm tall, clamps 3.6–7.6 cm wide

# 3. bind a figure to its caption
docxkit.figure_paragraph(doc, path)  # keep_with_next = True
```

Justified Chinese in Word stretches short lines glyph by glyph. `顶点纵坐标`
became `顶 点 纵 坐 标` in a rendered page — the single ugliest bug of the whole
build, and invisible in the source.

Figure sizing: a fixed `width=Cm(5.6)` gives a wide circuit diagram 2.7 cm of
height (unreadable) and a tall triangle 6.9 cm (half a page). Target a height
and derive the width from the PNG's own aspect ratio.

### Equations

```python
from examfig import omml
omml.add_tex(paragraph, r"I=\dfrac{U}{R}=\dfrac{6\ \mathrm{V}}{6\ \Omega}=1\ \mathrm{A}")
```

Produces a real Word equation object, editable in Word, not an image.

**Use `\stackrel`, never `\xrightarrow`.** The latter lowers to `m:limUpp` +
`m:phant`, which renders as an empty box. And `\longrightarrow` has no glyph in
Cambria Math at all.

Chinese inside an equation needs a font patch:

```python
omml._patch_cjk(node, font="SimSun")   # adds w:rFonts to CJK runs only
```

Without it, `点燃` above a reaction arrow is a row of tofu boxes.

---

## 5. Verifying before delivery

```python
from examfig import figcheck

ok, lines = figcheck.check(
    [{"no": 1, "need": ["G", "G_par", "G_perp", "30"], "text": "如图1"}],
    {1: {"marks": result["marks"]}})
```

Then render the document and look at it:

```bash
node /path/to/libreoffice-kit/lib/cli.js render --input paper.docx --output-dir preview/
```

Two things you will see that are **not** bugs:

* **Grey hairline boxes around figures.** LibreOffice's preview draws a border
  during import. Verify by unpacking: `w:pBdr`, `a:ln`, `v:shape` all zero
  occurrences, `pic:pic` counting your images. Word shows no border.
* **Thin frames around equations.** Same import-time artefact. `m:ctrlPr` and
  `a:ln` are absent from the XML.

Two things that **are** bugs, and only rendering reveals them:

* A label sitting on top of a curve.
* A figure whose labels spill outside the canvas, which `bbox_inches="tight"`
  then expands into a nearly blank page.

---

## Checklist

Before shipping a paper with figures:

- [ ] Every `need` label in `figcheck` passes.
- [ ] Every `如图 N` in every stem has a corresponding figure N.
- [ ] Organic reactions use `→`, inorganic use `=`.
- [ ] Chemical formulae use subscript runs, not OMML.
- [ ] Every equation renders as an equation, not a box.
- [ ] Figures are 3.6–7.6 cm wide, 4.3 cm tall.
- [ ] Every figure has a caption `图 N（示意图）` bound to it with
      `keep_with_next`.
- [ ] The document has been rendered and every page looked at.

# Third-party notices

`dsh-exam-fig` itself is MIT licensed (see [LICENSE](LICENSE)). It depends on
the Python packages below at runtime. None are vendored in this repository:
they are downloaded into a separate `vendor/` directory by
`python -m examfig.figdeps` (see the README), so this project ships no
third-party code and its own MIT grant is unaffected by their terms.

All dependencies carry permissive licences compatible with MIT redistribution.
The two `Apache-2.0` entries are compatible but carry a separate
`NOTICE`-preservation obligation; nothing here modifies their sources.

## Required

| Package | Version tested | Licence | Role |
| --- | --- | --- | --- |
| matplotlib | 3.11.2 | PSF-based (matplotlib licence, BSD-compatible) | all 2D drawing |
| numpy | 2.5.4 | `BSD-3-Clause AND 0BSD AND MIT AND Zlib AND CC0-1.0` | geometry, projection |
| schemdraw | 0.23 | MIT | circuit symbols and layout |
| rdkit | 2026.09.1 | BSD-3-Clause | molecular structure rendering |
| python-docx | 1.2.0 | MIT | `.docx` assembly |
| lxml | 6.1.3 | BSD-3-Clause | OMML transform, XML handling |
| latex2mathml | 3.81.1 | MIT | LaTeX → MathML |

## Transitive

| Package | Version tested | Licence |
| --- | --- | --- |
| contourpy | 1.4.0 | BSD-3-Clause |
| cycler | 0.12.1 | BSD (matplotlib project) |
| fonttools | 4.68.0 | MIT |
| kiwisolver | 1.5.1 | Modified BSD (Kiwi) |
| packaging | 26.3 | `Apache-2.0 OR BSD-2-Clause` |
| pyparsing | 3.3.3 | MIT |
| python-dateutil | 4.0.0 | BSD-3-Clause |
| pillow | 13.0.0 | MIT-CMU |
| tzdata | 2026.6 | Apache-2.0 |
| mpmath | 1.3.0 | BSD |
| sympy | 1.14.0 | BSD |

`mpmath` and `sympy` are optional: nothing in `examfig/` imports them. They were
used while validating the drawing geometry during development and are listed
here because an earlier vendor bundle included them.

### Notes on the compound licences

* **numpy** ships vendored components under `0BSD`, `MIT`, `Zlib` and `CC0-1.0`
  in addition to its own BSD-3-Clause. `CC0-1.0` imposes no attribution
  requirement; the others require preserving their notices, which numpy does
  inside its own distribution.
* **packaging** is dual-licensed `Apache-2.0 OR BSD-2-Clause`; the BSD-2-Clause
  arm is the simpler fit here.
* **tzdata** and **packaging** under the Apache-2.0 arm require keeping their
  `LICENSE` text if redistributed. This project does not redistribute them.

## Not a dependency: MML2OMML.XSL

Converting LaTeX to native Word equations uses `MML2OMML.XSL`, which is part of
Microsoft Office and is **not** redistributed here. The plugin looks for it on
the local machine and degrades gracefully (equations fall back to plain text)
when Office is absent. Using a file that ships with Office does not change this
project's licence.

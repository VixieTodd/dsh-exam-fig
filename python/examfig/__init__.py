# -*- coding: utf-8 -*-
"""examfig -- parameterised exam figures for maths / physics / chemistry.

The package is organised around one idea: **a figure is a derived artefact of
the numbers in the question, never a hand-drawn illustration.**  Every drawing
function takes the same parameters the prose uses, computes the geometry from
them, and returns both the PNG and the set of labels it actually painted on the
canvas.  That returned label set is what makes automated proof-reading
possible (see :mod:`examfig.figcheck`).

Public surface:

    env            runtime bootstrap (vendor path, matplotlib cache, CJK font)
    omml           LaTeX -> native Word equations
    chem           chemical formula runs with real subscripts
    labelplace     label placement optimiser for point annotations
    figcheck       figure/question consistency verification
    docxkit        python-docx helpers shared by the paper builder
    figures        the drawing functions, one module per figure family
    registry       name -> drawing function, plus parameter metadata
"""

__version__ = "0.1.0"

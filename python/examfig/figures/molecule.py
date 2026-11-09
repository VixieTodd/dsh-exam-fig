# -*- coding: utf-8 -*-
r"""Structural formulae from SMILES, drawn by RDKit.

This is not "drawing something that looks like ethanol".  RDKit parses the
SMILES string into a molecular graph and lays out the bonds from it, so a
typo in the SMILES shows up as a different molecule rather than as a cosmetic
difference.

The molecular formula comes from ``CalcMolFormula`` on the same parsed
molecule, which is what makes the fourth-level check meaningful: if the SMILES
is edited, both the picture and the asserted formula change together.
"""
import os

from .. import env


def molecule(smiles_list, out_path="chem_structure.png", sub_size=(340, 270),
             background=(255, 255, 255)):
    """Render one or more structures side by side.

    Returns the formulae, which double as the figure's marks.
    """
    env.bootstrap()
    from rdkit import Chem
    from rdkit.Chem import Draw, rdMolDescriptors

    if isinstance(smiles_list, str):
        smiles_list = [smiles_list]

    mols, formulas = [], []
    for smi in smiles_list:
        m = Chem.MolFromSmiles(smi)
        if m is None:
            raise ValueError("bad SMILES: %r" % (smi,))
        mols.append(m)
        formulas.append(rdMolDescriptors.CalcMolFormula(m))

    img = Draw.MolsToGridImage(
        mols,
        molsPerRow=min(len(mols), 2),
        subImgSize=tuple(sub_size),
        useSVG=False,
        legends=None,
    )
    parent = os.path.dirname(os.path.abspath(out_path))
    if parent:
        os.makedirs(parent, exist_ok=True)
    img.save(out_path)

    return {"formulas": formulas, "smiles": list(smiles_list),
            "marks": set(formulas)}


def condensed(formula):
    """Condensed structural formula as chemical-formula parts.

    Convenience wrapper so a question can show ``CH3CH2OH`` with real
    subscripts without going through RDKit.
    """
    from ..chem import parse_formula
    return parse_formula(formula)

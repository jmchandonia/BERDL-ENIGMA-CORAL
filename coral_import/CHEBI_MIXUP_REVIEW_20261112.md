# ChEBI term mix-ups in existing bricks (review 2026-11-12)

Scope: every ChEBI term used in a variable or dimension-variable definition (66 terms) or as a dimension value (449
terms) of the 1,952 bricks in sync-20261111-195223 (820 current). Method: flag non-element terms in element-type bricks
(five or more "... atom" terms) and amino-acid, residue, charged or zero-valent forms anywhere; confirm identities from
the isotope masses stored in the Adams core-pilot bricks and from the source column order.

## A. Wrong compound (element symbol resolved to another ChEBI term) - five current bricks

| Brick | Name | Wrong term -> intended |
| --- | --- | --- |
| Brick0000072, Brick0000073 | adams_metals_corepilot_271 / _106 | lysine -> K (mass 39); L-proline residue -> P (31); L-valine residue -> V (51); L-tryptophan residue -> W (182); L-selenocysteine residue -> U (235, 238); Gly-D-Ala -> Ga (71); arsane -> As (75); polysulfur -> Sn (118); lead(2+) -> Pb |
| Brick0000059, Brick0000062 | hazen_corepilot_xrf_trace_106 / _271 | L-selenocysteine residue -> U; arsane -> As; polysulfur -> Sn; silver(0) -> Ag; mercury(0) -> Hg; lead(2+) -> Pb (26-element XRF list) |
| Brick0000081 | hazen_field_100ws | lysine -> K; L-selenocysteine residue -> U; Gly-D-Ala -> Ga; arsane -> As; silver(0) -> Ag; lead(2+) -> Pb; chlorine atom -> chloride; butyryl group -> probably bromide (the anion block is Cl, ?, NO3, PO4, SO4 and the survey measured Br) |

Brick0000007 had the same errors and is replaced by Brick0002178. helium(0) in Brick0000072/73/80 is a "presence of
helium" flag for the ICP-MS collision mode and in Brick0000081 a dissolved gas: both intended.

## B. Right compound, imprecise form

- `phosphorus(.)` (CHEBI:30207) for elemental P in seven current Adams ICP-MS bricks (Brick0000080, 1916, 1920-1923, 2145;
  the term comes from the ELEMENTS table of `tools/build_sso_batch_ab_coral_import.py`); `phosphorus atom` (CHEBI:28659) is meant.
- `L-valine residue` for L-valine in 144 current high-throughput growth bricks; `L-asparagine residue` and
  `L-histidine residue` in 65 current growth bricks each (carbon and nitrogen source plates).
- `uranium(0)` in Brick0000060, Brick0000063, Brick0002147; `glycine residue` in Brick0000068 (metabolomics).

## Not affected
Brick0000010 adams_metals_100ws and the other element bricks use the "... atom" terms correctly.

## Fixing
Group A needs superseding bricks (molecule terms are data). Group B is cosmetic; the phosphorus term should at least be
corrected in the builder's ELEMENTS table before the next Adams metals brick.

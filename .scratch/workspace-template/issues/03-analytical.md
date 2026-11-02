# 03 Analytical: copv-analytical, phase 01

Status: blocked by 01 (and by 02's library step, since the study pins `copv`)

Read `../spec.md` first.

## The paper

Hondekyn, Pastrello, Ali & Van Paepegem, "An analytical framework to predict the 3D stress field in pressurised, thick-walled composite shells of revolution", Composite Structures (2026), DOI `10.1016/j.compstruct.2026.120059` (ScienceDirect PII S0263822326000243). It is paywalled: add it with `ws refs add 10.1016/j.compstruct.2026.120059 --repo copv-analytical`; if `ws fetch` cannot retrieve the PDF, ask the user to drop it in the pool as `papers/<citekey>.pdf` and stop until it is there.

## The study

**Question:** does the paper's analytical framework predict the 3D stress field of a filament-wound COPV, dome included, accurately enough to serve as a fast "fidelity level 0" of the copv library (screening, the M3 fidelity link, M6 optimisation)? Claims are checked first, then adoption is decided.

Rule packs: `literature-check`, `fe-simulation`. Spawn with `ws spawn analytical`; it pins `copv` and uses the library's data model (vessel, layup, materials), not its Nastran mesher or writer.

**Planned phases** (fixed in `PLAN.md`; only phase 01 is done in this ticket):

1. **01 digest and register** (explore): digest the paper (digest-source skill, against the PDF, pages cited); claim register (quotation, page, metric, published number); reproducibility audit (are the equations complete, every case fully specified: geometry, layup, materials, loads, BCs? are code and data public?); prior-work check in the hub; a proposed protocol for the phases below.
2. **02 reproduction**: an independent reimplementation of the framework (not derived from any author code; author code, if public, is only a comparison arm) reproducing the paper's own cases against its published numbers (`reproduction` evidence).
3. **03 dolfinx reference**: an FE reference in dolfinx, in the study, in its own conda environment (`environments/copv-fem.yml`, the D8 pattern; spimat's `spimat-plasticity/fem/README.md` shows it working on r2d2), with mesh convergence per the `fe-simulation` pack; on the paper's cases first.
4. **04 reference vessel**: Van Bavel's reference vessel (literature data, already in the library's `vessel/reference.py`): analytical vs dolfinx, dome and transition region.
5. Later, not planned in detail: Nastran validation on the workstation; an adoption ADR in `copv`, the dolfinx code entering the library through `copv.experimental` if it proves itself.

D3 and every ECOHYDRO demonstrator are excluded: no project values enter this study.

## Do (this ticket)

1. Spawn the study; write `PLAN.md` (question, claim type: comparative against a published result plus verification, packs, phases table).
2. Phase 01 in full (above), committed locally.
3. **Stop.** Do not start phase 02 or freeze any protocol.

## Done when

The phase 01 note, the digest, the claim register and the proposed protocol are committed, `ws check` is clean, and the report to the user lists: the claims, what is reproducible and what is not, the proposed protocol, and the questions the user must settle before phase 02 (to be grilled).

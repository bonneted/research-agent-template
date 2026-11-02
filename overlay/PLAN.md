# Plan

What this study sets out to show, fixed before the runs that show it. Terms follow `../{{hub}}/docs/CONTEXT.md`; the rules this plan answers to are the core rules in `AGENTS.md` and the rule packs below.

## Question

<!-- The research question, in one or two sentences, and its scope. -->

## Claim type

<!-- comparative | feasibility | scientific, and the evidence each claim needs: the matched
     axis and effect rule, the scaling curves and the classical reference, or the
     verification case and the engineering quantities. -->

## Rule packs

The packs of `rules/` this study follows besides the core rules, one per line (`- fe-simulation`), each with any rule it sets aside and why.

<!-- - ml-training
     - fe-simulation
     - uq-reliability
     - literature-check -->

## Protocol

Fixed before a confirm phase's first run, then frozen (`uv run python -m study.protocol freeze phases/NN-slug`). The text before the first `###` holds for every phase; a phase's own protocol is its `### NN-slug` subsection.

<!-- Hypotheses, arms, calibration case, primary metric and headline estimator, uncertainty
     and how it is estimated, baseline and its setting, budget, decision rules. -->

## Phases

| Phase | Type | Level | Budget | Question | Status |
|---|---|---|---|---|---|

## Canary runs

The reference runs rerun after any library pin bump, solver or environment change, or change to `study/` (core rule 8): one or two, each a phase and a seed whose stamped run is the reference. Drift beyond the stated uncertainty is a deviation, logged below, and flags the hub findings it touches.

| Phase | Seed | Reference run | Watched metric | Uncertainty |
|---|---|---|---|---|

## Deviations

A departure from the protocol, a library pin bump, an environment change or a rule set aside, logged when it happens. The Phase column starts with the phase's number or name (`02-burst`): a refrozen protocol needs its row.

| Date | Phase | Deviation | Decided before or after launch | Why |
|---|---|---|---|---|

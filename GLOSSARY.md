# Knowledge tree

The vocabulary of the kit: how research is organised into inquiries, how a result becomes knowledge, and what keeps it honest. An inquiry's own `GLOSSARY.md` holds its domain terms; these are the terms every inquiry shares, and its `AGENTS.md` uses them.

## Language

### The tree

**Inquiry**:
A repository that owns one research question, at any breadth, with its wiki, findings, plan and code.
_Avoid_: study (a bounded piece of work, wrong at the root), project, workspace, node

**Knowledge tree**:
The inquiries of one research effort, each nested in its parent's `inquiries/` folder, from the broadest question at the root to the narrowest at the leaves.
_Avoid_: workspace, monorepo

**Root inquiry**:
An inquiry with no parent.
_Avoid_: hub, main repo

**Sub-inquiry**:
An inquiry whose question is part of its parent's; cloned into the parent's `inquiries/<name>/`.
_Avoid_: child repo, study

**Spawn**:
Creating a sub-inquiry from the parent's kit (zooming in).

**Adopt**:
Making an existing inquiry a sub-inquiry of a new or existing parent (zooming out). Merging two inquiries is a new root and two adopts.

**Detach**:
Undoing an adopt: the inquiry becomes a root again, keeping a copy of the constraints it inherited.

**Route**:
A sub-inquiry's entry in its parent's index: its question, status, and what to dive there for.

**Coverage**:
How a parent's sub-inquiries cover its question: the routes, the sub-questions still open, and what is out of scope and why.

**Lowest common ancestor**:
The nearest inquiry above two branches; where a source or concept both use is digested.

### Knowledge

**Finding**:
A claim an inquiry has established, one note with a status and its evidence.
_Avoid_: result (a run's output), conclusion

**Status**:
`hint`, `confirmed`, `retracted` or `superseded`; set only by `publish-finding` and `review-finding`.

**Evidence kind**:
What an evidence item is: `run`, `derivation`, `reproduction`, `source`, `measurement`, `legacy` or `sub-inquiry`; each carries the fields that make it checkable.

**Phase**:
One step of an inquiry, explore or confirm, with its folder, its note and its consolidation level.

**Consolidation level**:
How much a phase spends to ground its answer: `scout`, `build` or `publish`.

**Denominator**:
How many variants, analyses or runs were tried to reach a finding.

**Digest**:
A wiki note on one source: what the inquiry uses or rejects from it.
_Avoid_: summary

### Rules

**Core rule**:
One of the twelve rules in every inquiry's `AGENTS.md`.

**Fixed rule**:
A core rule never set aside: every number traces, source claims grounded, negatives and the denominator published, the tree never strengthens a claim, the human confirms, and off-limits material.

**Adjustable rule**:
A core rule an inquiry may set aside, with its reason in `PLAN.md`.

**Rule pack**:
Rules for one kind of work (`rigour`, `fe-simulation`, …), selected by an inquiry in addition to the core rules.

**Guardian**:
The agent's duty to name the rule a request would break, the bias it guards against and the compliant alternative, before acting.

**Off-limits material**:
Documents, data or connectors an agent must never read, listed out of git in `.off-limits.yaml` and inherited down the tree.

### The kit

**Kit**:
What an inquiry carries: its `AGENTS.md`, skills, rule packs and skeleton files (`kit/` in this repository), plus the `rkt` tool, pinned.
_Avoid_: template (this repository, which holds the kit and the tool)

**Pool**:
The one folder outside git holding every document, code resource and dataset; each inquiry's `resources/` links to it.

**Resource manifest**:
An inquiry's `references.bib` and `resources.yaml`, from which its share of the pool can be rebuilt.

# Inquiry

<!-- One or two lines: this inquiry's question and its scope, as in inquiry.yaml. Written when the inquiry starts. -->

This repository is an **inquiry**: it owns one question, at any breadth, and is one node of a **knowledge tree**. Start from `docs/wiki/index.md`. Terms are in `GLOSSARY.md`, the question, rules and phases in `PLAN.md`, decisions in `docs/adr/`, relations in `inquiry.yaml`.

## The knowledge tree

- **Parent.** When `inquiry.yaml` names a `parent`, the parent's repository is `../..` (this inquiry sits in its `inquiries/<name>/`). Without one, this inquiry is a root, and works the same.
- **Sub-inquiries** are cloned into `inquiries/<name>/`, out of this repository's git, and listed in `inquiry.yaml`. A broad question is answered by decomposing it into sub-inquiries plus this inquiry's own synthesis. This inquiry runs its own phases only for work no child owns (integration, cross-cutting comparison); a phase whose question fits under one child's belongs in that child.
- **Down**, a child receives its question and the constraints this inquiry holds: the core rules as tightened in `PLAN.md`, the rule packs, pinned libraries. It may tighten them, never loosen them. It reads this inquiry's notes by link, never copies them.
- **Up**, a child gives findings, and nothing else, through `publish-finding`. This inquiry's own findings speak its question's terms and cite a child's finding as `sub-inquiry` evidence. Detail stays at the level it belongs to.
- **Routing.** `docs/wiki/index.md` has a `## Sub-inquiries` section: each child with its question, status and what to dive there for; then the sub-questions still open; then what is out of scope and why. Asked a question broader than one note, read the index, pick a route, descend, repeat. Search across the tree only when no route matches.
- **Grow the tree** with the skills: `spawn` (a sub-inquiry), `adopt` (an existing repository as a sub-inquiry; merging two is a new root and two adopts), `detach`.

## Layout

- **`inquiry.yaml`**: the question, the parent, the sub-inquiries, the Zotero collection, the rule packs, the kit version. Tools read it; prose lives in the index.
- **`PLAN.md`**: the question, the claim type, the rules as adjusted (with why), the rule packs, the protocol, the phases with their level and budget, the deviations.
- **`docs/`**: `wiki/` (the memory, below), `findings/` (one note per finding, format in `docs/findings/finding-format.md`), `adr/`. `GLOSSARY.md` at the root: this inquiry's terms only; the parent's glossary holds the terms they share.
- **`phases/NN-slug/`**: one folder per phase, `NN` two digits (`03-mesh-convergence`), with its code and `config.yaml` (`type: explore | confirm`, `consolidation:`). Shared code beside it. Runs go to `runs/NN-slug/<run>/`, outside git, with the commit and the configuration written beside each output.
- **`rules/`**: the rule packs, copied when the inquiry was spawned; a pack changed upstream reaches this inquiry only by a copy logged as a deviation.
- **`resources/`**: the link to the resource pool, outside git and read-only: never edit it. Extract PDF text with `pdftotext`, or `pypdf` through uv.
- **`references.bib`** and **`resources.yaml`**: the resource manifest, below.
- Nothing derived is committed (runs, figures that a script makes, caches). A library is never edited from here: a change is a merge request to it, then a pin bump here, logged as a deviation.

## Core rules

Every inquiry follows these. **Fixed** rules are never set aside. **Adjustable** ones may be, for this inquiry and its children, with the reason in `PLAN.md`'s Rules section. The rule packs `PLAN.md` selects add to them.

*Planning*

1. **Explore or confirm** (adjustable). Each phase is one or the other. A confirm phase fixes its protocol in `PLAN.md` before its first run: the question, the method, the analysis (metric, comparison, how the uncertainty is computed), the sample size or stopping rule, and the result that would refute the claim. Deviations are logged. Only a confirm phase gives `confirmed`.
2. **Grounded knowledge per token** (adjustable). Each phase declares a consolidation level and a rough budget (tokens, counted runs) in `PLAN.md` and its `config.yaml`, and its note reports what it spent. The next level is reached by a later phase, never by default.
   - `scout` (default for explore): the fastest grounded answer; one known-case check; targets spot-checked; findings as `hint`, without review.
   - `build` (default for confirm): the protocol, verification tests, counted runs; findings as `hint`, without review.
   - `publish`: only to promote the hints the user names to `confirmed`; one `review-finding` reviewer for the phase's findings together, two rounds at most; what is not upheld stays `hint`.

*Evidence*

3. **Verification before results** (adjustable). A method is checked on a case with a known answer (analytical solution, published value, manufactured solution, control) before it produces a new result.
4. **Every number traces** (fixed): to a run (commit and configuration beside its output), a derivation, or a page of a source. Every number in a note has its unit.
5. **No selection on the reported metric** (adjustable). Settings are chosen on a case separate from the one evaluated.
6. **Uncertainty with every headline number** (adjustable): an estimate with its interval, from whichever applies (seeds, noise, discretisation, sampling). A p-value or "significant" is never the claim alone.
7. **A competent baseline** (adjustable). A comparison is against the strongest competing method, tuned with the same budget as the proposed one; both budgets are stated.

*Claims*

8. **Source claims are grounded, inferences are marked** (fixed). A claim from a source cites it with its page (`[@key, p. 7]`) and was checked against the passage. Your own inference is labelled as such. A reference enters only by its identifier, through `refs add`.
9. **A claim states its scope** (adjustable): the conditions it was shown under; nothing extrapolates beyond them without a label. A claim about the physical world rests on validation evidence (a measurement), or says it holds for the model only.
10. **Negative results and the denominator are published** (fixed). A finding states how many variants, analyses or runs were tried to reach it, and the phase note lists them. Negative findings go up the tree like the others.

*The tree*

11. **The tree never strengthens a claim** (fixed). A finding is at most as strong as the weakest `sub-inquiry` evidence it rests on; a synthesis of hints is a hint.
12. **The human confirms** (fixed). The user approves a confirm protocol before its first run, and each promotion to `confirmed`, after a blind `review-finding`. Never certify your own work.

## When a request would break a rule

Say so before acting: name the rule, the bias it guards against, whether that bias matters here, and the way to do the task within the rule. Then the user decides. Overriding an adjustable rule is logged in `PLAN.md` as a deviation; a fixed rule is not overridden. Asked why a rule exists, answer the same way.

## A phase

1. **Prior work.** Before planning a phase, read what the tree already knows: this inquiry's findings, the parent's (`../../docs/findings/index.md`), and the children's routes. A retracted finding is a dead end, a hint a lead to confirm, a confirmed finding a starting point.
2. **Plan.** Add the phase to `PLAN.md`: its question, type, level and budget. A confirm phase writes its protocol, the user approves it, then it is frozen (with the rigour pack: its hash in `config.yaml`).
3. **Verify, then run.** Check the method on a known case (rule 3), then run. Write the phase note `docs/wiki/phases/NN-slug.md` as the phase goes: what was asked, what was tried (all of it), what happened, negative results included.
4. **Publish.** At the end of the phase, follow `publish-finding`: the findings go into `docs/findings/`, and the ones that answer the parent's question up to the parent.

## Findings

A finding is one note in `docs/findings/`, written by `publish-finding`. Its status is `hint`, `confirmed`, `retracted` or `superseded`; each evidence item has a kind (`run`, `derivation`, `reproduction`, `source`, `measurement`, `legacy`, `sub-inquiry`) with the fields `docs/findings/finding-format.md` gives it. Never edit a status by hand.

## The wiki

The wiki is the inquiry's memory, read by the user in Obsidian and by you. Before answering a question about the inquiry, read `docs/wiki/index.md` and the notes it links, and cite the notes you used.

- **Links** are relative Markdown links, `[sphere](../concepts/sphere.md)`, never `[[wikilinks]]`. They go to this inquiry, its parent or a child, never to a sibling or a cousin. A finding citing another inquiry's evidence also gives a permalink at a commit.
- **Indexes.** `docs/wiki/index.md` is the entry. Every notes folder has an `index.md`, one line per note. Every note is reachable from the entry.
- **Parsimony.** One note per source or concept. A note states what this inquiry uses or rejects from its subject, with a pointer to where it is used. A digest is a selection, never a full summary.
- **Shared knowledge lives at the lowest common ancestor.** When a source or concept digested in one branch is needed by another, it moves up (`update-wiki`), and each branch keeps only what it takes from it.

Keep the wiki current as part of the work, in the same turn:

- **New resource** in `references.bib` or `resources.yaml`, or newly in `resources/` → follow `.agents/skills/digest-source/SKILL.md`. A document an ancestor has digested gets no second digest: link it, and state what this inquiry takes.
- **Change** that adds a method, changes a result, or contradicts a note → follow `.agents/skills/update-wiki/SKILL.md`.

`rkt check` verifies the links, indexes, routes, findings and citations; run it before committing a change to `docs/`, and fix what it reports.

## Resources

- **`references.bib`** lists every document (cite as `[@citekey]`); **`resources.yaml`** every code resource at a pinned commit and dataset with its sha256. `rkt fetch` brings what they list into `resources/` and prints what is still missing.
- **Never write BibTeX.** Add a reference with `rkt refs add <DOI | arXiv id | URL>`; it prints the citekey. With a Zotero collection in `inquiry.yaml`, the reference is filed there and the `.bib` regenerated (`rkt refs pull` after editing in Zotero); a thesis, report or slides is added by the user in Zotero. Without one, `refs add` writes the entry itself.

## Working efficiently

- Before building an optional instrument (a digitiser, a diagnostics run, a sweep), name the claim it serves and build the cheapest one that answers it.
- Delegate well-scoped work to subagents on a smaller model: reviews against a checklist, searches, figure reading, `rkt check` fixes, wiki edits from a given diff. Keep derivations, method and protocol design, and the reading of results in the main session.
- Keep the context small: tool output near 50 lines at most (longer output goes to a file, then is searched), images cropped and read once, scripts that print summaries.

## Skills

In `.agents/skills/` (`.claude/skills` links to it). You reach for these yourself: `start-inquiry`, `digest-source`, `update-wiki`, `publish-finding`, `review-finding`, `spawn`. The user types `adopt`, `detach`, and `ask-tree` (what to do next, why a rule, upgrading the kit). They lean on [Matt Pocock's skills](https://github.com/mattpocock/skills), declared in `.claude/settings.json`, where they name them (`grilling`, `domain-modeling`, `tdd`).

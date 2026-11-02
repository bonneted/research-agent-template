# Spec: research-knowledge-tree

The research agent template becomes recursive. Every repository is an **inquiry**: it owns one question, at any breadth, and can grow sub-inquiries (zoom in) or be adopted into a broader one (zoom out). The tree of inquiries is a **knowledge tree**, from the broad question at the root to the narrow checks at the leaves. The workspace template (`research-ws-template`) is harvested into this repository and deleted; its hub, `ws` and overlay go.

Settled by a grilling session on 2026-11-02. Decisions are in `docs/adr/`; this spec is the whole picture and the delivery plan.

## Thesis

Agents make rigour affordable. Pre-registered protocols, verification on known cases, traceable numbers, published negatives and adversarial review used to cost more than most studies could spend; they no longer do. This repository is a handful of rules that make an agent do research that way, in one repository that can grow into a tree. The rules are the product; the kit is small.

## The inquiry (ADR 0001, 0002)

- An inquiry owns **one question**. Its breadth sets the depth of the subtree under it: a broad question is answered by decomposing it into sub-inquiries, plus the inquiry's own synthesis.
- A non-leaf inquiry does synthesis, and its own phases only for work no child owns (system-level integration, cross-cutting comparison). A phase whose question fits under one child's question belongs in that child.
- Sub-inquiries are cloned into `inquiries/<name>/`, gitignored by the parent. The folder tree is the knowledge tree: `../..` from a child's root is its parent. Each inquiry is an independent git repository and works standalone.
- `inquiry.yaml` (committed): `question`, `parent` (optional URL), `inquiries` (name, URL), `zotero_collection` (optional), `rule_packs`, `kit` (template URL at a tag, and the tool version). `resources.yaml` stays for code and data.
- **spawn** `<name>`: a new inquiry in `inquiries/<name>/` from the parent's kit; its question and inherited constraints; registered in `inquiry.yaml` and the routing section; its Zotero subcollection; then the alignment step.
- **adopt** `<url>`: clone into `inquiries/`; move its Zotero collection under the parent's; check its rules and off-limits against the inherited constraints and report conflicts for the user to settle (the child tightens); draft its route line from its index and findings; propose the shared sources to move up; the alignment step.
- **merge** of two repositories: a new root inquiry, then two adopts.
- **detach**: the reverse of adopt; the child keeps a copy of every inherited constraint it relied on.

## Flow (ADR 0003, 0004)

- **Down**: the question and the inherited constraints (core rules as tightened, rule packs, off-limits, pinned libraries). Knowledge by link to the parent's notes, never copied. A child tightens what it inherits, never loosens it. Off-limits is the one inheritance materialised by copy (a missing link would fail open).
- **Up**: findings only, one level at a time. A parent's finding about its own question cites the child's finding as evidence of kind `sub-inquiry`. Each level speaks its own question's terms.
- **The tree never strengthens a claim**: a parent's finding is at most as strong as its weakest supporting sub-inquiry evidence.
- **Routing and coverage**: every `docs/wiki/index.md` has a `## Sub-inquiries` section: one entry per child (link to its index, its question, status `active | closed | dormant`, "dive here for:" topics, quantities and methods, headline findings), then the sub-questions still open, then what is out of scope and why. The child updates its entry when it publishes upward. An agent asked at a broad scope reads the index, picks a route, descends, repeats; it searches across the tree only when no route matches.

## The wiki (ADR 0005)

- Standard relative Markdown links everywhere: `[sphere](../concepts/sphere.md)`. No `[[wikilinks]]`. Opening the root in Obsidian makes the whole tree one vault.
- `docs/wiki/index.md` is the entry; every notes folder (`sources/`, `concepts/`, `findings/`, `phases/`) has an `index.md`, one line per note.
- Every note is reachable from the entry index; every link resolves; links go to the same inquiry, the parent or a child, never to a sibling or cousin.
- A finding citing another inquiry's evidence also carries a permalink at a commit, so it reads correctly with the child not cloned.
- Shared knowledge lives at the lowest common ancestor: when a second branch needs a digest, it moves up, and both link up to it, each stating only what it takes. Part of `update-wiki`.

## Rules (ADR 0007, 0008, 0009, 0010)

Twelve core rules in `AGENTS.md`, in four groups. **Fixed** ones are never set aside; **adjustable** ones may be, with the reason in `PLAN.md` (Rules section). Wording to be finalised in slice 2; content:

| Group | Rule | Guards against | Kind |
|---|---|---|---|
| Planning | 1. Explore or confirm; a confirm protocol is fixed before its first run, deviations logged; only confirm gives `confirmed` | testing hypotheses suggested by the data | adjustable |
| Planning | 2. Grounded knowledge per token: each phase declares its consolidation level (`scout`, `build`, `publish`) and budget; the next level is a later phase, never the default | rigour spent where it is not needed; claims stronger than what was spent | adjustable |
| Evidence | 3. Verification before results: a method is checked on a case with a known answer (analytical solution, published value, control) before it produces a new result | silent method bugs read as findings | adjustable |
| Evidence | 4. Every number traces: to a run (commit and configuration beside the output; the full stamp in the rigour pack), a derivation, or a page of a source; every number in a note has its unit | untraceable or drifting numbers, unit errors | fixed |
| Evidence | 5. No selection on the reported metric: settings chosen on a case separate from evaluation | tuning on the test set, leakage | adjustable |
| Evidence | 6. Uncertainty with every headline number | false precision | adjustable |
| Evidence | 7. A comparison is against the strongest competing method at its best setting | straw-man baselines | adjustable |
| Claims | 8. Source claims are grounded, inferences are marked: a claim from a source cites its page and is checked against the passage; the agent's own inference is labelled as such | hallucination, citation laundering | fixed |
| Claims | 9. A claim states its scope: the conditions it was tested under; nothing extrapolates beyond them without a label | over-generalisation | adjustable |
| Claims | 10. Negative results are published, upward too | the file drawer | fixed |
| Tree | 11. The tree never strengthens a claim | status inflation on the way up | fixed |
| Tree | 12. The human confirms: the user approves a confirm protocol before it is frozen, and each promotion to `confirmed`, after a blind `review-finding` | agent self-certification | fixed |

Off-limits material is fixed too, stated in its own section rather than as a numbered rule.

- Moved out of the core: canary reruns, run stamp, protocol freeze, conda pins, units in code (pint) → **rigour pack** (`rules/rigour.md` with its small code); nothing-derived-committed and never-edit-the-library → layout section of `AGENTS.md`; token hygiene (smaller-model subagents for well-scoped work, tool output near 50 lines, images cropped and read once, summary-printing scripts) → a **Working efficiently** section of `AGENTS.md`.
- Domain rule packs (`fe-simulation`, `ml-training`, `uq-reliability`, `literature-check`) carried from the workspace template, optional.
- **Guardian**, always on in `AGENTS.md`: when a request would break a rule, name the rule and the bias it guards against, judge whether that bias matters here, offer the compliant alternative, and let the user decide. Overriding an adjustable rule is logged as a deviation; a fixed rule is refused.
- **Alignment step** at spawn and adopt, one screen: the twelve rules one line each with the active packs; the inherited constraints (read-only); "Keep the defaults, or adjust?" (Enter keeps); "Does this inquiry touch confidential material? Name the folders, patterns or connectors." (Enter: none). Adjusting grills only the named rules and writes `PLAN.md`'s Rules section.

## Findings (ADR 0008, 0009)

Carried from the workspace template, one level up instead of to a hub: statuses `hint | confirmed | retracted | superseded`; evidence kinds `run`, `derivation`, `reproduction`, `source`, `measurement`, `legacy`, and new `sub-inquiry`; one note per finding in the inquiry's `docs/findings/`, indexed by theme. `publish-finding` writes a child's findings into the parent in one commit and updates the route entry. `review-finding` is a blind reviewer before `confirmed`.

## Kit (ADR 0006, 0013, 0014, 0015)

- **Text, copied into each inquiry**: `AGENTS.md` (rules, layout, flow, guardian, working efficiently), `CLAUDE.md` importing it, the skills, `rules/`. Spawn copies the parent's; an `upgrade` path in `ask-tree` diffs against a newer template tag and applies it with the user's approval.
- **Skills** (8): `digest-source`, `update-wiki` (with move-up), `publish-finding`, `review-finding`, `spawn`, `adopt`, `detach`, `ask-tree` (router: next action, explaining a rule, pointing to the right mattpocock skill, upgrade). Each names the mattpocock skill it leans on (grilling in alignment, domain-modeling for the glossary and ADRs, tdd for phase code) instead of restating it.
- **Tools**, one `uv tool` pinned in `inquiry.yaml` (`uvx research-knowledge-tree@<version> <command>`): `refs` (add, pull), `fetch`, `check`, the off-limits hook. No Python copied into inquiries.
- **`check`**: links resolve; every note reachable from the entry index; no sideways links; `inquiry.yaml` sub-inquiries ↔ routing entries; finding statuses and evidence fields; rule 11 (no parent finding stronger than its sub-inquiry evidence); citekeys in `references.bib`; off-limits files present and a superset of the inherited set. One line per violation, non-zero exit. The rigour pack adds its own checks.
- **mattpocock skills**: declared in `.claude/settings.json` (`extraKnownMarketplaces`, `enabledPlugins`) at a pinned release; README fallback for other harnesses. The glossary file takes the name that release's `domain-modeling` uses (`CONTEXT.md` in 1.2.3; check the latest release in slice 2).

## Resources (ADR 0011)

- `references.bib` plus a pool of files per citekey is the contract; Zotero is one adapter.
- **With Zotero** (recommended): collections mirror the tree (`<root>/<child>/…`); `refs add` files into the inquiry's collection and regenerates its `.bib`; ZotMoov moves attachments into one folder, the pool; `fetch` resolves citekey → attachment path through Zotero 7's local API (`localhost:23119`), because ZotMoov's linked files never reach the web API. File names stay ZotMoov's.
- **Without Zotero**: `refs add` writes the entry into `references.bib` from Crossref, DataCite or arXiv; `fetch` looks for `<citekey>.pdf` in the pool, then open access (arXiv, Unpaywall). A `.bib` exported from any manager works.
- Mode detected, not configured: a Zotero key in the environment and a collection in `inquiry.yaml`.
- The pool is outside git, read-only for agents; `resources/` in each inquiry links to it (or one environment variable names it).

## Off-limits (ADR 0012) — to confirm

The names of off-limits material must not be committed, since an inquiry may be public. Proposed: the list lives in a gitignored `.off-limits.yaml` beside `inquiry.yaml`; spawn and adopt copy the inherited union into the child and write the guards (deny rules and hook in `.claude/settings.json`, `.ignore`); `check` verifies the child's set is a superset of its parent's when the parent is present. A fresh clone is unguarded until the user restores the list; the README and the alignment step say so.

## README

1. The thesis (rigour made affordable), then the tree in one paragraph.
2. Start in five minutes: one inquiry, the starter prompt.
3. The rules on one screen.
4. Growing the tree: spawn, adopt, merge, detach; routing and coverage.
5. Resources: two-minute bib-only path; ten-minute Zotero + Better BibTeX + ZotMoov path.
6. Harness notes: Claude Code, others; mattpocock skills; Windows links.

## Delivery

One branch, `knowledge-tree`; each slice reviewed by the user before the next; a merge request at the end.

1. **Harvest and delete**: copy from `research-ws-template` what is kept (rules packs, findings format, skills, `refs`/`fetch`/hook/links code, tests); then delete it (confirm with the user first).
2. **Core text**: `AGENTS.md` with the twelve rules, flow, guardian, working efficiently; `inquiry.yaml`; glossary; index skeletons with the routing section.
3. **The tool and `check`**: package as a `uv tool`; `check` and its tests.
4. **Resources**: `refs` bib-only mode; `fetch` through Zotero's local API (ZotMoov) and the pool; tests.
5. **Skills**: the eight, with the alignment step; mattpocock dependency in `.claude/settings.json`.
6. **Off-limits**: `.off-limits.yaml`, inheritance by copy, the hook, `check`.
7. **README** and the setup guide.
8. **Rename** to `research-knowledge-tree` (confirm with the user first), then the merge request.

Later, separately: migrate copv-ws onto the tree.

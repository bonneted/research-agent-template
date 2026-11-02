# Research workspace template

This repository is the workspace template: the hub of a research workspace at birth, and the source of `ws`. `ws init <name>` makes a workspace's hub from it, filling this opening from `skeleton/`. Working on the template itself: keep it free of any workspace's names, run `uv run python -m pytest` and `uvx ruff check`, and record a decision in `docs/adr/`. Terms follow `docs/CONTEXT.md`.

## The workspace

Every repository of the workspace is a sibling of the hub, in the hub's parent folder, named as in `workspace.yaml`: the hub, the library if there is one, one repository per study (`<name>-<topic>`), apps, and an off-limits repository if any. Relative paths between them always hold (`../<hub>`). A study never edits the library: a library change is a library merge request, then a pin bump in the study.

## The hub's role

- Findings, with their status and evidence, published from the studies by `publish-finding`, reviewed by `review-finding` before they are confirmed.
- Digests of the sources two studies or more use, and the domain's concept notes, in `docs/wiki/`.
- The workspace glossary (`docs/CONTEXT.md`), its ADRs (`docs/adr/`), its roadmap.
- `workspace.yaml`, `ws` (`tools/ws/`), the study overlay (`overlay/`), the rule packs (`rules/`), and the hub skills (`skills/`).

Everything else stays in its study. The hub cites studies by permalinks at a commit, so its committed notes read correctly without any study checked out.

## Running `ws`

Run it from the hub; `README.md` says what each command prints and when it fails.

- **`uv run ws sync`**: clone what is missing, link the pool, mount the studies, link the hub skills, write the off-limits files. Read its `FAILED` lines first.
- **`uv run ws fetch`**: pull every `references.bib` from Zotero, then bring every resource the manifests list into the pool.
- **`uv run ws refs add <doi | arXiv id | URL>`** and **`uv run ws refs pull`**: a repository's `references.bib` from its Zotero collection (`--repo <name>` for another). Never write BibTeX.
- **`uv run ws spawn <topic>`**: a new study.
- **`uv run ws check`** (`--repo <name>`, `--all`): findings, citations, phases, protocol freezes, rule packs, conda environments and off-limits files against the rules. Run it before committing a finding.
- **`uv run ws freeze <phase> --repo <study>`**: freeze a confirm phase's protocol (in the study: `uv run python -m study.protocol freeze phases/<phase>`).

## Layout

- **`docs/`** is the Obsidian vault: `CONTEXT.md`, `adr/`, `wiki/`, `findings/` (one note per finding, format in `docs/findings/finding-format.md`, indexed by theme in `findings/index.md`) and `studies/` (the committed study index, and the local mounts). Link notes with `[[note-name]]`. Tooling and the manifest stay outside it.
- **`overlay/`** is what `ws spawn` puts on the research agent template to make a study; **`rules/`** the rule packs it copies into each study; **`skills/`** the hub skills that `ws sync` links into every repository; **`skeleton/`** the hub's own text at birth, used by `ws init`.
- **`resources/`** is the link to the pool, outside git and read-only. The hub's own resources are those its manifest lists. Extract PDF text with `pypdf` through uv.
- **`references.bib`** is the hub's reference list, written by `ws refs pull` from its Zotero collection; add to it with `ws refs add`, never by hand. Cite in docs as `[@citekey]`, with the page for a number: `[@key, p. 7]`.

## Findings and evidence

A finding is published only through `publish-finding`, from a study, at the end of a phase. Its status is `hint`, `confirmed`, `retracted` or `superseded`; each evidence item has a kind (`run`, `derivation`, `reproduction`, `source`, `measurement`, `legacy`) with the fields `docs/findings/finding-format.md` gives it. Only a confirm phase gives `confirmed`, never legacy or source evidence alone, and only after `review-finding` upholds it. Never edit a finding's status by hand.

## Off-limits material

When `workspace.yaml` has `off_limits`, the paths, patterns, connectors and repository it lists are off-limits: never open, search, list, convert or `git show` them, never ask the user to paste their content, and never write their content anywhere. The hook in `.claude/hooks/` blocks calls that name them; when it blocks one, do not look for another way in. When a task needs a value from that material, stop and ask the user, naming the quantity, its unit and what it is for, and offer a fallback (a literature value, a made-up value of the right magnitude, or a parameter left open). Code takes such values as inputs, never as constants; tests use literature or made-up values. Prefer the Grep tool to a recursive shell search, which the hook cannot see into.

## The wiki

Before answering a question about the workspace, read `docs/wiki/index.md` and the notes it links, and cite the notes you used. When a claim comes from a document, check it against the passage in its source form or PDF.

Keep the wiki current as part of the work, in the same turn:

- **New resource** in `references.bib` (by `ws refs add`) or `resources.yaml`, or newly in the pool → follow `.agents/skills/digest-source/SKILL.md`.
- **Change** that adds a method, changes a result, or contradicts a note → follow `.agents/skills/update-wiki/SKILL.md`.

**Parsimony rule:** one note per source or concept. A note states what the workspace uses or rejects from its subject, with a pointer to where it is used. A digest is a selection, never a full summary.

## Hub skills

The hub skills are in `skills/`, linked by `ws sync` into every repository's `.agents/skills/`, beside the hub's own template skills there. `publish-finding` is run from a study at the end of a phase: it writes the phase's findings into the hub in one commit and links them from the phase note. `review-finding` reviews a finding adversarially before it is confirmed. `ask-<name>`, typed by the user anywhere in the workspace, answers what to do next; when a command, lifecycle step or skill changes, change its map too.

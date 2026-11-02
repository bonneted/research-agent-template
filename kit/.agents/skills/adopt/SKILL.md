---
name: adopt
description: Adopt an existing repository as a sub-inquiry of this one (zoom out; merging two is a new root and two adopts).
disable-model-invocation: true
---

# Adopt an inquiry

Run in the parent: an existing inquiry, or a new root made for the purpose (`rkt init`, then `start-inquiry` with a question both adopted repositories answer part of).

1. **Clone** the repository into `inquiries/<name>/` (`git clone <url> inquiries/<name>`). If it has no `inquiry.yaml` (a repository from before the kit, or the research agent template), run `rkt init` in it: the kit fills what is missing and keeps every file already there; then say which of its files the kit kept, so the user can merge the kit's text into them.
2. **Relations.** Set `parent` in the child's `inquiry.yaml` and list the child in this one's. Add this inquiry's rule packs the child lacks.
3. **Zotero.** When both have collections, ask the user to move the child's collection under this one's in Zotero, then set its `zotero_collection` to the new path and run `rkt refs pull` in the child.
4. **Rules.** Compare the child's `PLAN.md` Rules section with what this inquiry holds. A rule the child set aside that this inquiry keeps is a conflict: list each for the user, with what the child's findings rest on it. The child tightens, or the user changes this inquiry's rule; record the outcome in both `PLAN.md`s.
5. **Align.** In the child, follow the Alignment part of `start-inquiry`.
6. **Route.** Read the child's index and findings, and write its route under `## Sub-inquiries` in `docs/wiki/index.md`: its question, status, what to dive there for, its headline findings. Remove any open line it now covers.
7. **Shared sources.** List the sources both this inquiry (or another child) and the adopted one digest: propose moving each up (`update-wiki`, Move up).
8. **Findings up.** For the child's findings that bear on this inquiry's question, follow the Up part of `publish-finding`.
9. **Check and commit** both, after `rkt check --tree` passes: `Adopt <name>` here.

Done when the child is cloned and listed with its parent set, every rule conflict is settled in both plans, its route is written, and `rkt check --tree` passes.

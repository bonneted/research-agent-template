---
name: ask-tree
description: Ask what to do next anywhere in a knowledge tree, why a rule exists, or how to upgrade the kit.
disable-model-invocation: true
---

# Ask the tree

Answer the user's question with the **next action**: the command to run, the file to edit, or the skill to type. Read the file a line below points to before answering from it: the map says where the answer lives, those files are the truth.

**Where you are.** Run `rkt check` first and read its output. Then `inquiry.yaml` (the question, the parent, the children), `PLAN.md` (the phases table, the deviations), `git status`, and the index's `## Sub-inquiries` section. A question broader than this inquiry: read the parent's index (`../../docs/wiki/index.md`) and route from there.

## The lifecycle

1. **Start**: `rkt init` in an empty folder, then `start-inquiry`.
2. **Sources**: `rkt refs add <DOI | arXiv | URL>`, `rkt fetch`, then `digest-source`.
3. **A phase** (`AGENTS.md`, "A phase"): prior work, plan in `PLAN.md` (type, level, budget), verify, run, write the phase note. Test-first code: `tdd`. A design question: `prototype`. A run that misbehaves: `diagnosing-bugs`. A protocol to stress-test before freezing: `grilling`.
4. **Publish**: `publish-finding` at the end of a phase; `review-finding` comes with it at the `publish` level.
5. **Grow the tree**: `spawn` to zoom in on part of the question; `adopt` to put an existing repository under this one, or under a new root that merges two; `detach` to let a child stand alone.
6. **Keep the wiki true**: `update-wiki` after code changes, and to move a shared note up to the lowest common ancestor.

## Commands

`rkt --help` lists them; the ones a user asks about:

- `rkt check [--tree]`: the rules a machine can tell, one line per problem.
- `rkt fetch [--tree]`: the bibliography from Zotero, then every resource into the pool, and what is still missing.
- `rkt refs add <id>` / `rkt refs pull`: never BibTeX by hand.
- `rkt freeze phases/NN-slug`: the rigour pack's protocol freeze.

## Explaining a rule

Asked why a rule exists, or whether to set it aside: name the rule (`AGENTS.md`, "Core rules", or `rules/<pack>.md`), the bias it guards against, whether that bias matters for this inquiry, and the way to work within it. The user decides; an adjustable rule set aside goes in `PLAN.md`'s Rules section, a fixed one stays.

## Upgrading the kit

`inquiry.yaml` records the kit version (`kit.version`). For a newer one: install it (`uv tool install --force git+<kit.template>@v<version>`), run `rkt init` in an empty temporary folder, and diff its files against this inquiry's `AGENTS.md`, skills and `rules/`. Show the user each change, apply the ones they accept (their own tightenings in `PLAN.md` stay), set `kit.version`, and run `rkt check`.

## Matt Pocock's skills

Declared in `.claude/settings.json`, installed when the folder is trusted: `grilling` (interviews), `domain-modeling` (`GLOSSARY.md` and ADRs), `tdd`, `prototype`, `diagnosing-bugs`, `research` (primary sources on a question), `to-spec` and `to-tickets` (a large phase as a spec, then small tickets). Their names change between releases: list the installed ones when unsure.

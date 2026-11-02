---
name: spawn
description: Spawn a sub-inquiry for part of this inquiry's question. Use when the user asks to zoom in, split off, or open a sub-inquiry, or takes on an open line of the index.
---

# Spawn a sub-inquiry

1. **The part.** Agree with the user on the sub-question: one part of this inquiry's question, ideally an open line under `## Sub-inquiries` in `docs/wiki/index.md`, and on a short name (`burst-fdm`: lowercase words joined by dashes). It must not overlap a child's question; if it does, it belongs in that child.
2. **The repository.** Ask the user for its remote URL (or create it with `gh`/`glab` if they say so). Then, in this inquiry:

   ```bash
   git clone <url> inquiries/<name>    # or: mkdir inquiries/<name> && git -C inquiries/<name> init
   rkt init inquiries/<name> --question "<the sub-question>"
   ```

3. **Relations.** In the child's `inquiry.yaml`: `parent` (this inquiry's remote URL), `rule_packs` (at least this inquiry's), and `zotero_collection` as this inquiry's collection plus `/<name>`, when this inquiry has one; create that subcollection in Zotero, or ask the user to. In this inquiry's `inquiry.yaml`, add the child under `inquiries`. Copy any rule pack of `rules/` the kit lacks into the child's `rules/`.
4. **Route.** Under `## Sub-inquiries` in `docs/wiki/index.md`, replace the open line with the child's route: `- [<name>](../../inquiries/<name>/docs/wiki/index.md): <question>. Active. Dive here for: <topics, quantities, methods>.`
5. **Start it.** In the child, follow `start-inquiry`: its interview starts from this inquiry's question, and its alignment shows what it inherits.
6. **Commit** the child (`Start the inquiry`) and this inquiry (`Spawn <name>`), after `rkt check --tree` passes here.

Done when the child is cloned in `inquiries/<name>/` with its question, rules and parent, this inquiry lists and routes to it, and `rkt check --tree` passes.

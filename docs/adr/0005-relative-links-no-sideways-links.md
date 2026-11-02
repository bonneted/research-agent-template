# Relative Markdown links, an index per folder, and no sideways links

Notes link with standard relative Markdown links, `[sphere](../concepts/sphere.md)`: Obsidian follows them, forges render them, and an agent opens the path as written. `[[wikilinks]]` are ambiguous once the vault spans a tree. `docs/wiki/index.md` is the entry; every notes folder has an `index.md`, one line per note; every note is reachable from the entry, and every link resolves.

Links go to the same inquiry, its parent or a child, never to a sibling or a cousin, so a subtree can be detached or adopted without breaking links. What two branches share lives at their lowest common ancestor: when a second branch needs a digest, it moves up (`update-wiki`) and both link to it, each stating only what it takes. A finding citing another inquiry's evidence also carries a permalink at a commit, so it reads correctly without the child checked out.

## Consequences

`check` verifies all of it. Moving a note means rewriting links to it, which `update-wiki` does.

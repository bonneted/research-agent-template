# Sub-inquiries are nested, gitignored clones, and the folder tree is the knowledge tree

A sub-inquiry is cloned into its parent's `inquiries/<name>/`, which the parent's git ignores; the parent's `inquiry.yaml` lists each with its URL. `../..` from a child's root is always its parent, so an agent walks the tree without reading configuration, and opening the root in Obsidian makes the tree one vault. Each inquiry stays an independent repository that works standalone; it knows a parent only through the optional `parent` of its `inquiry.yaml`.

Zooming in is **spawn**; zooming out is **adopt** (clone an existing inquiry under a new or existing parent); merging two repositories is a new root and two adopts; **detach** reverses adopt, the child keeping a copy of every inherited constraint it relied on.

## Considered options

- **Git submodules**: the same nesting with the child's commit pinned by git; heavy for agents and on Windows, and evidence already pins commits by permalink.
- **Siblings in one folder** (the workspace template): the tree lives only in manifests, and relative paths break as depth grows.

## Consequences

A parent's commit does not pin its children's; a finding citing a child does, by permalink.

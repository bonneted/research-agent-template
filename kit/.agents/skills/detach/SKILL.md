---
name: detach
description: Detach a sub-inquiry so it stands as a root of its own.
disable-model-invocation: true
---

# Detach a sub-inquiry

Run in the parent.

1. **What it relied on.** In the child, list what it inherits by link: the parent's Rules section and rule packs, and every link from its notes up to the parent (`grep -rn "\.\./\.\./\.\./\.\." inquiries/<name>/docs` and the like).
2. **Make it whole.** In the child: copy into its `PLAN.md` Rules section the inherited rules it follows; for each link up to a parent note, write the part it needs in its own note (a digest of a shared source, with the citekey added by `rkt refs add`) and link that instead; remove `parent` from its `inquiry.yaml`. Its findings keep their permalinks.
3. **The parent.** Remove the child from `inquiries` in `inquiry.yaml` and its route from `docs/wiki/index.md` (keep an out-of-scope line saying where the work went); the parent's findings that cite the child keep their permalinks, which stay valid.
4. **Move it out.** Tell the user the child can now be moved out of `inquiries/`, and its Zotero collection out of the parent's.
5. **Check** both: `rkt check` in the child (now a root) and in the parent, and commit each.

Done when the child passes `rkt check` with no link or rule depending on the parent, and the parent no longer lists or routes to it.

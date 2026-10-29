# The hub cites studies by permalink; mounts are local only

A committed hub note cites a study by a permalink to a file at a commit, and must read correctly without any study checked out. For browsing and searching, `ws sync` also mounts each study's notes inside the hub vault as uncommitted links, so Obsidian shows one graph and an agent's prior-work check greps every study at once. Obsidian links do not cross vaults, so a hub that only linked would lose the graph and the search, and a hub that only mounted would break on any machine missing a clone.

Taken from the spimat workspace (its ADR 0003).

## Considered options

- **Mount the hub inside each study as well.** Rejected: hub → study and study → hub links form a cycle that Obsidian and recursive search walk forever. A study reads the hub at `../<hub>`.

## Consequences

`ws check` resolves each evidence permalink in the local clone of its study: the commit must exist there, and a run's phase must have the type the finding claims.

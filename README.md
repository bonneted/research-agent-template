# Research workspace template

A template for a research workspace: independent study repositories that each answer one question, a hub that receives only what the studies establish, one pool of resources outside git, Zotero-driven bibliographies, and `ws`, the tool that builds and checks it all. Guards against the usual research flaws are built in: core rules every study follows, rule packs for kinds of work, run stamps and a protocol freeze that refuse what breaks them, `ws check` for what a machine can tell, and an adversarial review before a finding is confirmed.

It is the hub of a workspace at birth: `ws init <name>` makes `<name>-hub` from it. It grew out of the spimat workspace's hub (`spimat-hub`), whose `ws`, overlay and skills it generalises, and it wraps the [research agent template](https://gitlab.kuleuven.be/r2d/collaboration/research-agent-template), kept as its `template` remote, from which every study is spawned. Why it is built this way is in `docs/adr/`.

## A workspace

Every repository of a workspace is a sibling in one folder, the workspace root, named as in the hub's `workspace.yaml`:

```
copv-ws/                     the workspace root (not a repository)
  resources/                 the pool: papers/<citekey>.pdf, code/<name>/, data/<name>; outside git
  .claude/  .ignore          the off-limits files, written by ws sync (sessions start here)
  copv-hub/                  the hub: findings, digests, glossary, ADRs, workspace.yaml, ws, hub skills
  copv/                      the library, if the workspace has one: pinned by every study
  copv-<topic>/              a study: one question, its phases, runs and notes
  copv-confidential/         an off-limits repository, if any: cloned, never read
```

Relative paths between them always hold (`../copv-hub`). Roles are `hub`, `library`, `study`, `app` (a tool on the library, with no phases) and `off-limits`.

What the hub holds: findings (only through `publish-finding`), digests of sources used by two studies or more, domain concept notes, the workspace glossary and ADRs, the roadmap, `workspace.yaml`, `ws`, and the hub skills. Everything else stays in its study. A private library keeps its own design context; only a public one has its private context in the hub's `docs/library/`, which `ws sync` then points the library's agent to.

## Start a workspace

Install [uv](https://docs.astral.sh/uv/) and git, clone this template anywhere, and run `ws init` from the folder that will be the workspace root:

```bash
mkdir -p ~/copv-ws && cd ~/copv-ws
uv run --project ~/research-ws-template ws init copv \
  --gitlab https://gitlab.kuleuven.be/r2d/researchers/me/copv \
  --library copv --off-limits off-limits.yaml
```

`init` makes `copv-hub` from the template's last commit: the template is its `ws-template` remote (`--template-url`, by default the template's own `origin`), `origin` is `<gitlab>/copv-hub.git`. It writes `workspace.yaml` from the flags, fills the openings of `README.md`, `AGENTS.md` and `docs/CONTEXT.md` and the skill `ask-copv` from `skeleton/`, commits, and runs `ws sync`. On a terminal it asks for what the flags leave out; `--no-input` never asks, for agents. Nothing is created on GitLab: create the hub's project there and push (`git -C copv-hub push -u origin HEAD`). From then on run `ws` from the hub: `cd copv-hub && uv run ws sync`.

### The manifest

```yaml
workspace:
  name: copv                       # prefixes repositories, ask-copv, and COPV_RESOURCES, COPV_SSH_HOST
  gitlab: https://gitlab.kuleuven.be/r2d/researchers/me/copv   # the group of the repositories
  zotero_root: copv                # each repository's Zotero collection is copv/<repository>
  library: copv                    # optional: the library studies pin; may be listed later
  stamp_extras: copv.stamp:collect # optional: module:function adding fields to every run stamp
  rule_packs_dir: rules            # the hub's rule packs, copied into each study
  off_limits:                      # optional: see "The off-limits module"
    paths: [confidential/, copv-confidential/, ~/VISIATIV/]
    patterns: [{pattern: '\.(xlsx|docx|msg)\b', what: an Office or e-mail file}]
    deny_connectors: [mcp__claude_ai_Gmail, mcp__claude_ai_Google_Drive]
    repo: copv-confidential
template: https://gitlab.kuleuven.be/r2d/collaboration/research-agent-template.git
repositories:                      # keep it the last key: ws spawn appends to it
  - name: copv-hub
    url: https://gitlab.kuleuven.be/r2d/researchers/me/copv/copv-hub.git
    role: hub
```

A repository joins the workspace by a line under `repositories`; a repository line may name its Zotero collection by key (`zotero_collection: <key>`) when it is not `<zotero_root>/<name>`. The library or off-limits repository named in `workspace` may be listed later: until then `ws spawn` refuses to pin a library that is not listed.

## Add a study

```bash
uv run ws spawn burst
```

`spawn` creates `copv-burst` beside the hub: it clones the research agent template (`template` in the manifest), keeping it as the `template` remote, removes what a study does not need (`src/`, the template's own fetch and refs commands and their tests, its `resources/README.md` and lock), applies the overlay (`overlay/`, `{{key}}` filled in), copies the rule packs into `rules/` and the protocol freeze into `study/protocol.py`, pins the library at the commit of its default branch, and commits. It says "study" wherever the template's Markdown says "project" and sends its fetch and refs commands to the hub. It registers the study in `workspace.yaml` and `docs/studies/index.md`, creates its Zotero collection `<zotero_root>/copv-burst` when the key can write, and syncs. Its `origin` is `<gitlab>/copv-burst.git`; creating that project, pushing, and committing the hub's two changed files are left to you, as its output says. It refuses a topic already in the manifest or a folder already there, and leaves nothing behind when it fails.

A study's agent guidance, with the core rules and the phase workflow, is `overlay/AGENTS.md`; its plan skeleton is `overlay/PLAN.md`.

## Evidence and rules

**Findings.** A study publishes what its phases establish as findings in the hub, `docs/findings/<slug>.md`, each `hint`, `confirmed`, `retracted` or `superseded` ([finding format](docs/findings/finding-format.md)). Each evidence item has a kind: `run` (a stamped computation), `derivation` (an analytical result and the test or CAS script that checks it), `reproduction` (a published number reproduced, with its tolerance), `source` (a cited passage, checked against the PDF), `measurement` (a dataset with its sha256) or `legacy` (a result from before the workspace, which never supports `confirmed`). Only evidence from a confirm phase gives `confirmed`, and only after the `review-finding` skill, an adversarial reviewer with no study context, has upheld it.

**Core rules**, in every study's `AGENTS.md`: explore or confirm phases, verification before results, every number traces, no selection on the reported metric, uncertainty with every headline number, a competent baseline, negative results published, canary reruns after any version change, nothing derived committed and the library never edited from a study, units everywhere.

**Rule packs**, in `rules/`, selected per study in its `PLAN.md`: `ml-training`, `fe-simulation`, `uq-reliability`, `literature-check`. A workspace adds its own packs to the hub's `rules/`.

**Tooling that refuses.** `study/stamp.py` stamps each run with the study commit (and the diff of a dirty tree), the library's install, the configuration, the seed, the conda environments it used (by the hash of `conda list --explicit`), the hardware and the wall-clock, plus the workspace's `stamp_extras`. It refuses a confirm run from a dirty tree, or from a `PLAN.md` whose protocol is not the one frozen for the phase (`uv run python -m study.protocol freeze phases/NN-slug`, or `ws freeze NN-slug --repo <study>`).

**Environments uv cannot install** (a FE solver, say) are conda environments declared in the study as `environments/<name>.yml` with exact pins, never sharing a process with the uv environment: a run calls them with `conda run -n <name>`.

## `ws check`

```bash
uv run ws check              # the repository it is run from
uv run ws check --repo copv-burst
uv run ws check --all        # every repository, and the workspace root
```

It exits non-zero on a `FAILED` line, so a repository's CI can run it. It checks:

- each finding's front matter: its status, each evidence item's kind and required fields, `confirmed` only with non-legacy evidence from a confirm phase and a `reviewed` verdict of `upheld`, `superseded_by` for a superseded one;
- each evidence permalink: its commit (and file) in the local clone of the study, and the type of the phase a run's note belongs to;
- each `[@citekey]` in `docs/` against the repository's `references.bib` or the hub's (the hub also accepts its studies'); a number beside a citation that gives no page is a warning;
- each `phases/NN-slug/` has its note `docs/wiki/phases/NN-slug.md` and a type; a confirm phase is frozen (a warning until its first run) at its current protocol, and refrozen only with a deviation logged;
- the rule packs `PLAN.md` selects are in the study's `rules/`;
- each declared conda environment that exists on this machine matches its pinned file;
- the off-limits files are present and current.

It reads only the clones and conda: nothing goes to the network, and the off-limits repository is never read.

## The off-limits module

For material an agent must never read: confidential documents, a partner's data, e-mail. Configured by `off_limits` in the manifest (or at `ws init`, by `--off-limits <file>` or the flags `--off-limits-path`, `--off-limits-pattern`, `--deny-connector`, `--off-limits-repo`):

- `paths`: globs, relative (`confidential/`, `**/resources/secret/`), `~/`-relative or absolute (`D:/Projects/X/WP*/`);
- `patterns`: regular expressions on a tool call's arguments, each a string or `{pattern, what}`;
- `deny_connectors`: connectors the agent may not use (`mcp__claude_ai_Gmail`);
- `repo`: a repository `ws sync` clones but never links, mounts, lists or reads.

`ws sync` writes into every repository it may read and into the workspace root, where sessions start: `.claude/settings.json` (deny rules for `Read` on each path in each spelling, and for the connectors, and a PreToolUse hook; merged into an existing file, whose other keys are kept, and reported if it cannot be merged), the hook `.claude/hooks/guard_off_limits.py` (a link to the hub's `tools/ws/guard_off_limits.py`) with its patterns in `.claude/hooks/off-limits.json`, and `.ignore`, which Claude Code's Grep and Glob honour. Files a repository does not track are kept out of git by its `.git/info/exclude`; one it tracks is changed in place and reported, to be committed.

The hook blocks a Read, Grep, Glob, Bash or PowerShell call whose arguments name an off-limits path (however it is spelt: `D:\x`, `/mnt/d/x`, `~/x`) or match a pattern, and tells the agent to ask the user instead. Without its patterns file it blocks every call. A path is matched as a whole name, so a bare word that is also a folder's name (`ls confidential`) is blocked too.

Its limits, honestly: the hook sees only the call's arguments. A command that reaches the material without naming it (`grep -r x .` from a folder above it, a script that walks the tree, a symlink with another name) is not caught; the rules in `AGENTS.md` cover it, and the Grep tool, which honours `.ignore`, is preferred to a shell search. The deny rules apply to Claude Code's own tools only. Other agents and harnesses read none of these files. And the module protects only sessions started in the workspace root or a repository after `ws sync` has run.

## Windows

The workspace runs on Windows without admin rights or Developer Mode. Where `ws` makes a folder link on Linux (the `resources` link to the pool, the hub skills, `.claude/skills`, the study mounts in the hub), it makes a directory junction on Windows, which holds an absolute path. Where it needs a file link (the off-limits hook), it copies the file and records the copy's hash beside it in `.ws-copies.json`: a copy left as `ws` wrote it follows the hub's file, a copy edited since is kept and reported. A `.claude/skills` link a repository commits, which git checks out on Windows as a text file, is replaced by a junction and marked `skip-worktree`. Set `COPV_RESOURCES` to keep the pool elsewhere, such as on another drive.

## Running `ws`

`ws` builds and checks the workspace from `workspace.yaml`. Run it from the hub (`uv run ws ...`), or from a study with `uv run --directory ../copv-hub ws ... --repo <study>`.

`sync` clones every repository of the manifest that is missing and prints one line per repository: `cloned`, `ok`, or what needs attention (`dirty`, `behind`, `no upstream`). Existing clones are fetched to compare them with their remote, never merged or checked out. It links each repository's `resources` to the pool, kept out of git by the clone's `.git/info/exclude`; a real `resources/` folder in its place is left as is and reported, to be emptied into the pool. It mounts each study's `docs/` in the hub as `docs/studies/<name>`, a link kept out of git, and reports a study with no `docs/`, anything else in the mount's place, and a study missing from `docs/studies/index.md`. It links each hub skill (`skills/<name>`) into every repository's `.agents/skills/`, the hub's included, and `.claude/skills` to `.agents/skills` where the repository has none; a skill or a `.claude/skills` of the repository's own in their place is left as is and reported. It writes the off-limits files. When the hub has `docs/library/` (a public library's private context), it writes the library's `CLAUDE.local.md`, and `AGENTS.md` where the library commits none, both git-ignored, pointing there. It exits non-zero if a repository could not be cloned or checked, or if the manifest does not match the hub's folder; read the `FAILED` lines before going on.

`refs pull` rewrites a repository's `references.bib` from its Zotero collection in a fixed form, lists the entries it removed and warns of a removed one still cited in `docs/`, and gives an item with no citekey one, written back to Zotero. `refs add <doi | arXiv id | URL>` looks the identifier up in Crossref (then DataCite) or arXiv, adds the item to the collection (an item of the library with that exact identifier joins it instead), prints the citekey and pulls. A reference is added with `ws refs add`, never by writing BibTeX; a thesis, report or slides, by hand in Zotero then a pull. `ws` only adds to Zotero, never changes or deletes a value already set.

`fetch` first pulls every repository's `references.bib` from Zotero (one `zotero: skipped (<reason>)` line without a configuration or a network), then reads each repository's resource manifest: it retrieves each missing document's PDF from a local folder of `<citekey>.pdf` files, the Zotero Web API, arXiv, then Unpaywall; keeps one clone of each code resource in the pool, at the newest commit any repository pins; checks each dataset's sha256; and ends with what is still missing as one `rsync` command to paste on a machine whose pool has it (its host is `$COPV_SSH_HOST`, by default this machine's name).

The code is in `tools/ws/`, tested end to end in `tests/` against local bare repositories standing in for GitLab: `uv run python -m pytest`.

## Resources

The pool is `$<NAME>_RESOURCES`, by default `resources/` in the workspace root, laid out as `papers/<citekey>.pdf`, `code/<name>/` and `data/<name>`. A repository's resource manifest is two committed files:

- **`references.bib`**: every document as a Zotero item, written by `ws refs`.
- **`resources.yaml`**: code, cloned by `ws fetch` once for the workspace at the newest commit any repository pins; data, copied by hand into `data/<name>` and checked against its sha256. Quote commits and checksums: YAML reads a hash made only of digits as a number.

  ```yaml
  code:
    - name: solver
      url: https://gitlab.example.org/group/solver.git
      commit: "<full commit hash>"
      source_of: <citekey>   # optional: this repository is the source form of that document
      # or code_of: <citekey> | [<citekey>, ...]   # optional: it implements those documents' methods
  data:
    - name: burst-tests.csv
      source: where a good copy is kept
      sha256: "<sha256 of the file>"
  ```

Zotero and PDF retrieval are configured in `~/.config/research-ws/retrieval.yaml` (or under `$XDG_CONFIG_HOME`), outside git. Its top-level keys serve every workspace; a workspace's section under `workspaces` adds to them or overrides them:

```yaml
pdf_folder: /mnt/c/Users/me/OneDrive/Zotero   # PDFs named <citekey>.pdf, e.g. kept by ZotMoov
email: you@example.org                        # Unpaywall asks for one; without it, it is skipped
workspaces:
  copv:
    zotero:
      library: groups/1234567                 # or users/<id>
      api_key: <a key with write access to the library and its files>
    upload_pdfs: true                         # attach PDFs found on arXiv or Unpaywall to their Zotero item
```

A read-only key still pulls; `refs add`, the citekey write-back and uploads fail with "the Zotero key is read-only". To fill `pdf_folder` from Zotero, let ZotMoov move attachments into a synced folder with no subfolder pattern, and set Zotero's file renaming to `{{ citationKey }}`.

## Keeping up with the template

A hub keeps this template as its `ws-template` remote: `git fetch ws-template` and merge to take its fixes to `ws`, the overlay, the rule packs and the skills. A study keeps the research agent template as its `template` remote in the same way. An improvement to `ws` made in a hub goes back as a branch on this template, free of the workspace's names. Rule packs already copied into a study change there only by a copy logged as a deviation.

## License

[MIT](LICENSE).

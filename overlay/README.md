# {{study}}

A study of the {{workspace}} workspace: one research question. The question and the protocol are in [PLAN.md](PLAN.md), the results in the wiki (`docs/wiki/index.md`), the rules its agent follows in [AGENTS.md](AGENTS.md) and the packs of `rules/` that `PLAN.md` selects.

```
PLAN.md                        question, claim type, rule packs, protocol, phases, deviations
rules/                         the rule packs, copied from the hub at spawn
study/                         shared study code; stamp.py stamps each run, protocol.py freezes a protocol
phases/NN-slug/                run.py, report.py, config.yaml (type: explore | confirm)
environments/<name>.yml        conda environments with exact pins, for what uv cannot install
docs/wiki/phases/NN-slug.md    one note per phase
runs/NN-slug/<run>/            outside git; set {{runs_env}} to keep runs elsewhere
resources/                     link to the workspace's pool, made by ws sync
```

## Set up

The study lives in the {{workspace}} workspace, beside its hub. On a new machine, clone the hub and let it build the rest:

```bash
mkdir {{workspace}}-ws && cd {{workspace}}-ws
git clone {{hub_url}}
cd {{hub}} && uv run ws sync && uv run ws fetch
cd ../{{study}} && uv sync
```

The library, when the workspace has one, is pinned at a commit in `pyproject.toml`; `uv sync` installs that commit. Commit the `uv.lock` it writes. A conda environment of `environments/` is made with `conda env create -f environments/<name>.yml`.

## After spawning

`ws spawn` makes the study locally and registers it in the hub; it creates nothing on GitLab. Create an empty, private repository on GitLab at the URL of the `origin` remote (`git remote get-url origin`), then push with `git push -u origin HEAD`, and commit the hub's `workspace.yaml` and `docs/studies/index.md`.

The research agent template this study started from is the `template` remote: `git fetch template` and merge to take its improvements.

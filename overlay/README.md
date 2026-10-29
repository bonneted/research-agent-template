# {{study}}

A study of the spimat workspace: one research question answered with the [spimat](https://gitlab.kuleuven.be/r2d/public/spimat) library. The question and the protocol are in [PLAN.md](PLAN.md), the results in the wiki (`docs/wiki/index.md`), the rules its agent follows in [AGENTS.md](AGENTS.md).

```
PLAN.md                        question, claim type, protocol, phases, deviations
study/                         shared study code; stamp.py stamps each run
phases/NN-slug/                run.py, report.py, config.yaml (type: explore | confirm)
docs/wiki/phases/NN-slug.md    one note per phase
runs/NN-slug/<run>/            outside git; set {{runs_env}} to keep runs elsewhere
resources/                     link to the workspace's pool, made by ws sync
```

## Set up

The study lives in the spimat workspace, beside its hub. On a new machine, clone the hub and let it build the rest:

```bash
mkdir spimat-ws && cd spimat-ws
git clone {{hub_url}}
cd {{hub}} && uv run ws sync && uv run ws fetch
cd ../{{study}} && uv sync
```

The library is pinned at a commit in `pyproject.toml`; `uv sync` installs that commit. Commit the `uv.lock` it writes.

## After spawning

`ws spawn` makes the study locally and registers it in the hub; it creates nothing on GitLab. Create an empty, private repository on GitLab at the URL of the `origin` remote (`git remote get-url origin`), then push with `git push -u origin HEAD`, and commit the hub's `workspace.yaml` and `docs/studies/index.md`.

The research agent template this study started from is the `template` remote: `git fetch template` and merge to take its improvements.

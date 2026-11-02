# {{name}} hub

The hub of the {{name}} workspace: findings from the studies, the digests and concepts they share, the workspace glossary and ADRs, and `ws`, the tool that builds and checks the workspace from `workspace.yaml`. Its repositories are in the GitLab group {{gitlab}}.

Set up a machine:

```bash
mkdir {{name}}-ws && cd {{name}}-ws
git clone {{hub_url}}
cd {{hub}} && uv run ws sync && uv run ws fetch
```

Start a study with `uv run ws spawn <topic>`: it creates `{{name}}-<topic>`, registers it and syncs. Then create its project on GitLab, push it, and commit the hub.

The hub was made from the workspace template by `ws init`, and keeps it as the `ws-template` remote: `git fetch ws-template` and merge to take its fixes. The rest of this README is the template's manual.


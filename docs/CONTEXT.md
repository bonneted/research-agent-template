# Workspace

The vocabulary shared by the hub and every study of the workspace: how research is organised, how a result becomes knowledge, and what keeps it honest. A study's own `CONTEXT.md` holds its domain and method terms; this one holds the terms every study shares, and the domain terms the workspace settles once.

## Language

### Repositories

**Workspace**:
The set of repositories that make up the research effort, side by side in one folder, the workspace root, as listed in the workspace manifest.
_Avoid_: monorepo, project folder

**Workspace manifest**:
The hub's `workspace.yaml`: the workspace's name and settings, and every repository with its URL and role.
_Avoid_: config

**Hub**:
The repository holding the knowledge that outlives any one study: findings, shared digests, the glossary, the ADRs, the roadmap, and the workspace tool.
_Avoid_: wiki (a study has one too), knowledge base

**Library**:
The package the studies use and pin, when the workspace has one; a study never edits it.
_Avoid_: main repo, framework

**Study**:
An independent repository that answers one research question, in phases.
_Avoid_: project (the research agent template's word, for a repository with no studies), experiment

**App**:
A repository that uses the library as a tool and answers no research question; it has no phases and publishes no findings.
_Avoid_: tool study

**Off-limits repository**:
A repository `ws` clones but never reads, links or lists, holding material an agent must never read.
_Avoid_: private repo (every repository may be private)

**Template**:
The research agent template, the generic project skeleton every study is spawned from; and the workspace template, which every hub starts from.
_Avoid_: boilerplate, starter

**Overlay**:
The workspace's layer put on the research agent template when a study is spawned: its agent guidance with the core rules, its plan, the stamp.
_Avoid_: study template

**Pool**:
The one uncommitted folder holding every resource of the workspace, reached from each repository through its `resources` link.
_Avoid_: data folder, cache

### Research

**Phase**:
One step of a study, `phases/NN-slug/`, with one question, its runs and its note; explore or confirm.
_Avoid_: experiment, milestone

**Explore phase**:
A phase whose protocol may change as it goes; it can only give hints.
_Avoid_: pilot

**Confirm phase**:
A phase whose protocol is fixed and frozen in `PLAN.md` before its first run, its deviations logged; only it can give confirmed findings.
_Avoid_: preregistered study (it is a phase)

**Protocol freeze**:
The hash of a confirm phase's protocol, recorded in its configuration before its first run; a run whose protocol differs is refused.

**Deviation**:
A departure from the protocol, a library pin bump, an environment change or a rule set aside, logged in `PLAN.md` when it happens.

**Run**:
One execution of a phase, stamped with what it takes to reproduce it; it counts as evidence only if its stamp is complete.
_Avoid_: experiment, job

**Run stamp**:
The `stamp.json` of a run: study commit and diff, library install, configuration, seed, environments, hardware, wall-clock.

**Canary run**:
A reference run rerun after a library, solver or environment change, to see whether results drifted.

**Core rules**:
The rules every study follows, in its `AGENTS.md`.

**Rule pack**:
A set of rules for one kind of work (`fe-simulation`), selected per study in its `PLAN.md`.

### Knowledge

**Finding**:
A claim a study established, a note in the hub with its status and evidence.
_Avoid_: result (a result lives in a phase note), conclusion

**Status**:
A finding's standing: hint, confirmed, retracted or superseded; optionally marked recheck.

**Evidence**:
What supports a finding, each item of a kind: run, derivation, reproduction, source, measurement or legacy.

**Legacy evidence**:
A result produced before the workspace existed, without a stamp; it never makes a finding confirmed.

**Review**:
The adversarial reading of a finding by a reviewer with no study context, before it is confirmed; its verdict is upheld, narrowed or rejected.

**Prior-work check**:
The search of the hub's findings and every mounted study before a phase is planned.

**Digest**:
A note on one source, stating what the workspace uses or rejects from it; a selection, never a summary.

**Off-limits material**:
Documents, data or connectors an agent must never read, listed in the manifest's `off_limits`; a value from it is asked of the user.

## Relationships

- A **workspace** has one **hub**, at most one **library**, any number of **studies** and **apps**, and at most one **off-limits repository**.
- A **study** pins the **library** at one commit; moving the pin is a **deviation** followed by the **canary runs**.
- A **phase** produces **runs**; a **finding** cites them by permalink as **evidence**.
- A **confirm phase** has a **protocol freeze**; only it can make a finding **confirmed**, and only after a **review**.

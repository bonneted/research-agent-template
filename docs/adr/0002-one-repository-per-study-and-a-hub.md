# One repository per study, and a hub

Each study is its own repository, and knowledge shared between studies lives in one hub, not in a monorepo of studies. Studies are independent experiments: each has its own history, its own rules, its own run data and its own library pin, and each can be archived when it ends. A monorepo would make cross-study links easy but mix one study's churn and pin bumps into another's history, and give an agent working on one study the other studies' phases as clutter. The cross-study connection this gives up is a knowledge problem, and the hub solves it: findings, decisions and vocabulary go through the hub; code goes through the library.

Taken from the spimat workspace (its ADR 0001).

## Consequences

The hub receives only what the studies establish, through `publish-finding`; everything else stays in its study. A private library keeps its own design context: spimat put its library's private context into the hub only because that library is public.

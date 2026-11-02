---
name: start-inquiry
description: Start an inquiry: interview the user on its question, then align on the rules. Use in a folder fresh from rkt init or spawn, when an adopted inquiry needs aligning with its new parent, or when the user asks to start or re-scope an inquiry.
---

# Start an inquiry

## Question

1. **Interview** the user with the `grilling` skill, one question at a time with your recommended answer, until you can write: the question in one sentence, its scope (what is in, what is out), the claim type (comparative, feasibility, scientific, review), and what the user already knows. With a parent (`inquiry.yaml` names one), start from the parent's question and the open line of its index this inquiry takes on: this question is a part of that one.
2. **Write** the question in `inquiry.yaml` and as the opening line of `AGENTS.md`; the question, scope and claim type in `PLAN.md`; the first terms in `GLOSSARY.md` (the `domain-modeling` skill), only those this inquiry adds to its parent's.

## Alignment

3. **One screen.** Show the user, in one message:
   - the twelve core rules of `AGENTS.md`, one line each, grouped as there, the fixed ones marked;
   - with a parent, what this inquiry inherits, read from `../../PLAN.md` (its Rules section) and `../../inquiry.yaml` (its rule packs): it may tighten these, never loosen them;
   - the rule packs that fit the work (`rules/README.md`), with the one you recommend;
   - the question: "Keep these rules as they are, or adjust some?"
4. **Adjust**, only if asked: grill the user on the rules they name, one at a time, saying what bias each guards against and whether it matters here. Write the outcome in `PLAN.md`'s Rules section (each rule set aside or tightened, and why), the selected packs in `inquiry.yaml` and `PLAN.md`. A fixed rule is never set aside; an inherited one is never loosened.
5. **Rigour pack.** If it is selected, copy `rules/rigour/study/` to the inquiry's root as `study/` and say how a phase's `run.py` uses `study.stamp.run`.

## First steps

6. **Sources.** Digest every resource the manifest lists (`digest-source`); ask the user for the key papers if it lists none.
7. **Plan.** Propose a first phase in `PLAN.md`: its question, type, consolidation level and budget (rule 2).
8. **Check and commit.** Run `rkt check`, fix what it reports, and commit: `Start the inquiry`.

Done when `inquiry.yaml`, `AGENTS.md` and `PLAN.md` hold the question, the user has answered the alignment question, `PLAN.md` records any rule adjusted, and `rkt check` passes.

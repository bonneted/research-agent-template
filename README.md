# Research agent template

A project skeleton for doing research with an AI coding agent: your sources, a wiki the agent maintains, and your code in one folder.

The ideas behind it are in the talk *Doing research with AI agents*: [slides (PDF)](talk/doing-research-with-ai-agents.pdf).

```
resources/        papers (<citekey>.pdf), code, data, legacy material. Outside git, never edited
references.bib    the documents, pulled from Zotero  } the resource manifest:
resources.yaml    code at a pinned commit, data      } uv run fetch fills resources/
docs/             Obsidian vault
  wiki/           index.md, sources/ (one digest per resource), concepts/, reading-list.md
  CONTEXT.md      project vocabulary
  adr/            decisions
src/  tests/      code (Python + uv)
tools/fetch/      the fetch and refs commands
AGENTS.md         instructions for any agent. CLAUDE.md just imports it
.agents/skills/   digest-source, update-wiki. .claude/skills links to it
```

Everything the agent knows about your project is plain Markdown in this folder, so you can switch model (Claude, GPT, Gemini, open models) or harness (Claude Code, Codex, Gemini CLI, OpenCode…) and keep it. Nothing here depends on one of them: `AGENTS.md` is read by most harnesses, and the skills are plain Markdown recipes.

## Start a project

1. **Copy** this repo under a new name (on GitHub, *Use this template*), and delete `talk/`. Install [uv](https://docs.astral.sh/uv/) and the agent of your choice.
2. **Add sources.** Name your Zotero collection in `resources.yaml` and configure your Zotero key, then run `uv run fetch`: it pulls `references.bib` from the collection, downloads the PDFs it can (from Zotero, arXiv, Unpaywall), clones the code at its commit, and lists what is left to copy into `resources/` by hand. No Zotero? `uv run refs add <DOI>` writes the entries itself. Both are in [resources/README.md](resources/README.md).
3. **Paste the starter prompt** in the agent.
4. **Open `docs/` as a vault** in [Obsidian](https://obsidian.md) to browse the wiki and its graph.

Claude Code reads skills from `.claude/skills/`, a committed link to `.agents/skills/`. On Windows, git checks the link out as a plain text file unless symlinks are on: turn on Developer Mode, then

```powershell
git config core.symlinks true
Remove-Item .claude\skills; git checkout -- .claude/skills
```

### Starter prompt

```
This is a new research project. Interview me, one question at a time with your
recommended answer, about the research question, the scope and what I already know,
until you can write the project line in AGENTS.md and the first terms in
docs/CONTEXT.md. Then digest every resource in references.bib and resources.yaml
(digest-source skill), and propose a first plan as a short list of small, testable steps.
```

Afterwards, the day-to-day prompts are short: *"add 10.1016/j.jcp.2018.10.045 and digest it"*, *"digest the solver repository"*, *"what does the wiki say about X?"*, *"implement step 3, then update the wiki"*.

### Optional: a structured planning loop

The interview-then-plan of the starter prompt is a loop worth making systematic. [Matt Pocock's skills](https://github.com/mattpocock/skills) do it well and work in most harnesses (install them as their README says): a *grilling* skill interviews you until the plan is shared, others write it down as a spec, split it into small tickets, and implement them one at a time; a setup skill, run once, sets up where the tickets and domain docs live. They were written for software but fit research. Their names change from release to release: ask the agent which one fits, or use their router skill.

## Example: a 15-minute demo

Monte Carlo vs polynomial chaos for the tip deflection of a cantilever beam, δ = PL³/(3EI), with E, I and P uncertain. There's a closed-form answer to check the agent against.

1. *Interview me* (or the grilling skill): `I want to compare Monte Carlo and polynomial chaos expansion (PCE) for the tip deflection of a cantilever beam with uncertain E, I and P. Write the project line in AGENTS.md and docs/CONTEXT.md once we agree.`
2. `Find about 5 key papers on PCE for uncertainty propagation and Sobol sensitivity (Xiu & Karniadakis 2002, Sudret 2008, Blatman & Sudret 2011…) and add them with uv run refs add.` Then run `uv run fetch`, drop in the PDFs it lists as missing, and ask: `Digest the new papers.`
3. `Implement MC and PCE (chaospy) for the tip deflection, check mean and variance against the analytical result, compute first-order Sobol indices, then update the wiki.`
4. Open `docs/` in Obsidian: index, a source digest, the graph.

## Limits

Check citations and numbers against the PDF: agents can invent both. Whatever you give the agent goes to the model provider: check your institution's and your partners' rules before sharing unpublished data or papers under review.

## License

[MIT](LICENSE).

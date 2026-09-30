# Research agent template

A project skeleton for doing research with an AI coding agent: your sources, a wiki the agent maintains, and your code in one folder.

Introduced in the R2D talk *Doing research with AI agents* ([slides](https://kuleuven-my.sharepoint.com/:p:/g/personal/damien_bonnet-eymard_kuleuven_be/IQBK4bvp7q7dRLNW9tb_hbRNAa9u_0rz_Jy6gG6XreB1fV8?e=vPFlSq), KU Leuven login).

```
resources/        papers (<citekey>.pdf), code, data, legacy material. Outside git, never edited
references.bib    the documents, exported from Zotero  } the resource manifest:
resources.yaml    code at a pinned commit, data         } uv run fetch fills resources/
docs/             Obsidian vault
  wiki/           index.md, sources/ (one digest per resource), concepts/, reading-list.md
  CONTEXT.md      project vocabulary
  adr/            decisions
src/  tests/      code (Python + uv)
tools/fetch/      the fetch command
AGENTS.md         instructions for any agent. CLAUDE.md just imports it
.agents/skills/   digest-source, update-wiki. .claude/skills links to it
```

Everything the agent knows about your project is plain Markdown in this folder, so you can switch model (Claude, GPT, open models) or harness (Claude Code, Codex, OpenCode…) and keep it.

## Start a project

1. **Copy** this repo under a new name, then install [uv](https://docs.astral.sh/uv/) and your agent ([Claude Code](https://docs.claude.com/en/docs/claude-code) in VS Code, for instance). Claude Code reads skills from `.claude/skills/`, a committed link to `.agents/skills/`, so an edited skill is never stale. On Windows, git checks the link out as a plain text file unless symlinks are on: turn on Developer Mode, then

   ```powershell
   git config core.symlinks true
   Remove-Item .claude\skills; git checkout -- .claude/skills
   ```

2. **Install [Matt Pocock's skills](https://github.com/mattpocock/skills)** and run `/setup-matt-pocock-skills` in the project. It sets up the issue tracker and the domain docs the other skills use.
3. **Add sources.** Export `references.bib` from Zotero and list code and data in `resources.yaml`, then run `uv run fetch`: it downloads the open-access PDFs, clones the code at its commit, and lists what is left to copy into `resources/` by hand (see [resources/README.md](resources/README.md), which also shows how to let it fetch from your Zotero library).
4. **Paste the starter prompt** in the agent.
5. **Open `docs/` as a vault** in [Obsidian](https://obsidian.md) to browse the wiki and its graph.

### Starter prompt

```
/grill-me This is a new research project. Interview me about the research question,
the scope, and what I already know, until you can write the project line in AGENTS.md
and the first terms in docs/CONTEXT.md. Then digest every resource in references.bib and
resources.yaml (digest-source skill), and propose a first plan as issues (/to-tickets).
```

Afterwards, the day-to-day prompts are short: *"digest the new papers"*, *"digest the solver repository"*, *"what does the wiki say about X?"*, *"implement issue 3, then update the wiki"*.

## Example: a 15-minute demo

Monte Carlo vs polynomial chaos for the tip deflection of a cantilever beam, δ = PL³/(3EI), with E, I and P uncertain. There's a closed-form answer to check the agent against.

1. `/setup-matt-pocock-skills`
2. `/grill-me I want to compare Monte Carlo and polynomial chaos expansion (PCE) for the tip deflection of a cantilever beam with uncertain E, I and P. Write the project line in AGENTS.md and docs/CONTEXT.md once we agree.`
3. `Find about 5 key papers on PCE for uncertainty propagation and Sobol sensitivity (Xiu & Karniadakis 2002, Sudret 2008, Blatman & Sudret 2011…). Add their BibTeX to references.bib.` Then run `uv run fetch`, drop in the PDFs it lists as missing, and ask: `Digest the new papers.`
4. `Implement MC and PCE (chaospy) for the tip deflection, check mean and variance against the analytical result, compute first-order Sobol indices, then update the wiki.`
5. Open `docs/` in Obsidian: index, a source digest, the graph.

## Limits

Check citations and numbers against the PDF: agents can invent both. Unpublished data and papers under review go to the model provider, so check your institution's rules first.

# Research agent template

A project skeleton for doing research with an AI coding agent: your sources, a wiki the agent maintains, and your code in one folder.

```
resources/        papers (<citekey>.pdf) and legacy material. Outside git, never edited
references.bib    reference list, exported from Zotero
docs/             Obsidian vault
  wiki/           index.md, sources/ (one digest per paper), concepts/, reading-list.md
  CONTEXT.md      project vocabulary
  adr/            decisions
src/  tests/      code (Python + uv)
AGENTS.md         instructions for any agent. CLAUDE.md just imports it
.agents/skills/   digest-source, update-wiki
```

Everything the agent knows about your project is plain Markdown in this folder, so you can switch model (Claude, GPT, open models) or harness (Claude Code, Codex, OpenCode…) and keep it.

## Start a project

1. **Copy** this repo under a new name, then install [uv](https://docs.astral.sh/uv/) and your agent ([Claude Code](https://docs.claude.com/en/docs/claude-code) in VS Code, for instance). Claude Code reads skills from `.claude/skills/`, so mirror them once (and again whenever you edit one):

   ```powershell
   Copy-Item -Recurse -Force .agents\skills .claude\skills   # Windows
   ```
   ```bash
   mkdir -p .claude && cp -r .agents/skills .claude/          # macOS / Linux
   ```

2. **Install [Matt Pocock's skills](https://github.com/mattpocock/skills)** and run `/setup-matt-pocock-skills` in the project. It sets up the issue tracker and the domain docs the other skills use.
3. **Add sources.** Put PDFs in `resources/papers/` named by citekey, and export `references.bib` from Zotero (see [resources/README.md](resources/README.md)).
4. **Paste the starter prompt** in the agent.
5. **Open `docs/` as a vault** in [Obsidian](https://obsidian.md) to browse the wiki and its graph.

### Starter prompt

```
/grill-me This is a new research project. Interview me about the research question,
the scope, and what I already know, until you can write the project line in AGENTS.md
and the first terms in docs/CONTEXT.md. Then digest every PDF in resources/papers
(digest-source skill), and propose a first plan as issues (/to-tickets).
```

Afterwards, the day-to-day prompts are short: *"digest the new papers"*, *"what does the wiki say about X?"*, *"implement issue 3, then update the wiki"*.

## Example: a 15-minute demo

Monte Carlo vs polynomial chaos for the tip deflection of a cantilever beam, δ = PL³/(3EI), with E, I and P uncertain. There's a closed-form answer to check the agent against.

1. `/setup-matt-pocock-skills`
2. `/grill-me I want to compare Monte Carlo and polynomial chaos expansion (PCE) for the tip deflection of a cantilever beam with uncertain E, I and P. Write the project line in AGENTS.md and docs/CONTEXT.md once we agree.`
3. `Find about 5 key papers on PCE for uncertainty propagation and Sobol sensitivity (Xiu & Karniadakis 2002, Sudret 2008, Blatman & Sudret 2011…). Add their BibTeX to references.bib and tell me which PDFs to put in resources/papers.` Then drop the PDFs in and ask: `Digest the new papers.`
4. `Implement MC and PCE (chaospy) for the tip deflection, check mean and variance against the analytical result, compute first-order Sobol indices, then update the wiki.`
5. Open `docs/` in Obsidian: index, a source digest, the graph.

## Limits

Check citations and numbers against the PDF: agents can invent both. Unpublished data and papers under review go to the model provider, so check your institution's rules first.

# Matt Pocock's skills are a declared, pinned dependency

Interviewing the user, sharpening a glossary, recording ADRs and test-first code are done well by [Matt Pocock's skills](https://github.com/mattpocock/skills); restating them here would double the kit. So `.claude/settings.json` declares their marketplace and plugin at a pinned release, Claude Code offers to install them when a repository opens, and this kit's skills name the one they lean on (grilling in the alignment step, domain-modeling for the glossary and ADRs, tdd for phase code). Other harnesses install them as their README says.

## Consequences

Their file names are followed, not overridden: the glossary is the file the pinned release's `domain-modeling` writes. A new release is adopted by a bump and a check of those names.

# Your BrainWiki

Open this folder as a vault in the free Obsidian app. Your notes stay ordinary local Markdown. The AI connector reads only the curated folder explicitly selected in your separate private runtime configuration.

| Folder | Purpose |
|---|---|
| [00_Raw](00_Raw/README.md) | Incoming captures and proposals awaiting review |
| [01_Wiki](01_Wiki/index.md) | Approved knowledge and its map of contents |
| [02_Archive](02_Archive/README.md) | Preserved sources cited by knowledge notes |
| [03_Operations](03_Operations/README.md) | Dated decisions, checks and handoffs |
| [04_Prompts_&_Skills](04_Prompts_&_Skills/README.md) | Operating methods and note template |
| [05_Identity](05_Identity/README.md) | Your private goals, business, voice and source pointers |
| [Projects](Projects/README.md) | Project cabinets that route tasks to authoritative sources |

Flow: capture in Raw → review and approve → write/link knowledge in Wiki → preserve the source in Archive → reindex the curated folder → search and read through the agent. Obsidian browses the whole vault; retrieval defaults to `01_Wiki/` only. Retrieval never writes notes and does not watch edits: reindex manually after approved edits, or, if you chose to enable automatic indexing during setup, a check every five minutes rebuilds the index when approved files changed. Turning that on or off, pausing it and approving changed indexing rules are your decisions, not the agent's.

Start the agent in this root and read [AGENTS.md](AGENTS.md). Keep your retrieval configuration, local state and onboarding log in the separate private runtime folder. Community plugins, a cloud account, Sync and Publish are optional and unnecessary for this workflow. Back up the vault and runtime configuration privately; verify restoration separately.

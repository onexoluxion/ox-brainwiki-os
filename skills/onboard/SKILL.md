---
name: onboard
description: Guided onboarding that customizes OX BrainWiki OS to the user's business by asking questions and writing the answers into the user's own files.
---

# onboard

Six steps. Each step is re-runnable alone (`/onboard 3` runs step 3 only) and touches only its own files; re-running one step leaves every other step's files unchanged. Every write carries the date from the operating system clock, never a remembered one. A step the user skips writes `skipped <date>` into every placeholder it owns, never a default value. Install nothing. Ask the questions in the user's language; write the answers verbatim, in the user's words. All paths below are relative to the repository clone unless marked `<root>`. Record each step's outcome as one line in `identity/onboard-log.md`: `step N: done <date>` or `step N: skipped <date>`.

## Step 1: requirements check

Ask nothing. Run each command and record its exit code; a non-zero exit is a missing item, reported and not installed:

- `uv --version` (uv, the installer this repository pins its dependencies with)
- `uv python find 3.12` (Python 3.12; this release is Windows-only and needs it)
- `git --version` (Git)
- `claude --version` or `codex --version` (one agent CLI is enough; report which one answered)

Write the four results to `identity/onboard-log.md` under `## Requirements <date>`. Re-run: replaces that section only.

## Step 2: private folder and sources

Ask: (a) the root folder for your private knowledge (an existing folder is kept exactly as it is); (b) the notes subfolder under that root that holds Markdown notes (default answer: `notes`; it may be empty today); (c) up to three other sources the business relies on, each as name, where it lives, what it holds. Pointers only: nothing is copied or ingested.

Write `identity/sources.md`: `{{FILLED_DATE}}` = date; `{{ROOT_FOLDER}}` = (a) with forward slashes; `{{NOTES_FOLDER}}` = (b); `{{SOURCE_1_NAME}}`, `{{SOURCE_1_LOCATION}}`, `{{SOURCE_1_HOLDS}}` = the first row of (c), the same for rows 2 and 3, unused rows = `none`. If the notes folder does not exist, create it empty and say so. Re-run: rewrites `identity/sources.md` only.

## Step 3: identity

Ask: business name; what it sells and where (channels); one to three goals for the coming year; the operator's role and weekly hours limit; the agent's name, register (direct and dense, plain words, or formal), answer shape, and any banned words. Then offer the optional decision filters exactly once: "Do you want the three optional decision filters (Ghost Town, ARR, two-way doors) kept in your goals file?".

Write three files. `identity/business.md`: `{{BUSINESS_NAME}}`, `{{WHAT_IT_SELLS}}`, `{{CHANNELS}}`, `{{OPERATOR_ROLE}}`, `{{HOURS_LIMIT}}`, `{{FILLED_DATE}}`. `identity/goals.md`: `{{GOAL_YEAR}}`, `{{GOAL_1}}`, `{{GOAL_2}}`, `{{GOAL_3}}` (unused = `none`), `{{DECISION_FILTERS}}` = `accepted <date>` or `declined <date>`, `{{DAILY_LOG_MODULE}}` = `off`, `{{FRIDAY_AUDIT_MODULE}}` = `off` (both modules stay off unless the user asks for one by name), `{{FILLED_DATE}}`. `identity/agent-voice.md`: `{{AGENT_NAME}}`, `{{REGISTER}}`, `{{ANSWER_SHAPE}}`, `{{BANNED_WORDS}}` (none = `none`), `{{FILLED_DATE}}`. Re-run: rewrites these three files only; `identity/sources.md` is untouched.

## Step 4: first cabinet

Ask: the first project's name and one-line purpose; its two authoritative sources (name, location, what each decides); where results and dated handoffs for this project may be saved; one known gap (something the project cannot see or confirm today). Derive a folder slug from the project name (lowercase, hyphens).

Copy `cabinet/templates/PROJECT_INDEX.md` to `<root>/<slug>/PROJECT_INDEX.md` and `cabinet/templates/task-and-source-guide.md` to `<root>/<slug>/task-and-source-guide.md`, then replace: `{{PROJECT_NAME}}` = name; `{{PURPOSE}}` = purpose; `{{RELATIVE_GUIDE_REFERENCE}}` = `task-and-source-guide.md`; `{{NAME}}` = `ox-project-cabinet`; `{{VERSION}}` = the `metadata.version` in `skills/ox-project-cabinet/SKILL.md`; `{{PORTABLE_SOURCE_AND_PROVENANCE}}` = `skills/ox-project-cabinet/SKILL.md in this clone of OX BrainWiki OS`; `{{MAINTAINED_SOURCE_LOCATIONS_AND_SCOPE}}` = both sources with what each decides; `{{PERMITTED_EXISTING_DESTINATION}}` = the results location; `{{ACCESS_FRESHNESS_OR_COVERAGE_GAPS}}` = the gap. In the guide: `{{AS_OF_DATE}}` = date; duplicate the single table row so there is one row per source, then per row `{{TASK}}` = the task that source answers, `{{REFERENCE}}` = the source location, `{{AUTHORITY}}` = the source name, `{{EVIDENCE_AND_DATE}}` = what evidence it holds and as of when, `{{DESTINATION}}` = the results location; `{{KNOWN_GAPS}}` = the gap. Verify no `{{` remains in either file. Re-run: rewrites the two files in `<root>/<slug>/` only.

## Step 5: retrieval

Ask: one exact identifier the business uses (an order, certificate or ticket number that appears in a note) and one question in plain words whose answer is in a note. Confirm the notes folder from step 2 (`{{NOTES_FOLDER}}`).

Write `retrieval.config.json` in the repository clone with exactly these four keys (the connector rejects any other shape; relative paths resolve beside this file):

```json
{"root": "<root with forward slashes>", "state": ".state/onboard", "allow": ["<notes folder>"], "exclude": []}
```

Add to `exclude` any subfolder of the notes folder that must never be indexed, written as `<notes folder>/<subfolder>`. `.state/` is git-ignored; never commit it. Then run, from the clone, and record each exit code:

1. `.venv/Scripts/python.exe ox_retrieval.py index --config retrieval.config.json` (first run downloads the embedding model; `MODEL_PROVENANCE.json` names the revision)
2. `.venv/Scripts/python.exe ox_retrieval.py status --config retrieval.config.json` (expect `"fresh": true`)
3. Register `.venv/Scripts/python.exe ox_retrieval.py serve --config retrieval.config.json` as a stdio MCP server in the agent client, under the name `ox-retrieval`.

`search` and `read` are connector tools exposed by `serve`, not CLI subcommands (the CLI accepts only `serve`, `index`, `status` and `--config`). Through the connector call `search` with `query` = the identifier and `mode` = `exact`, then `search` with `query` = the question and `mode` = `semantic` (`scope` = the notes folder; `limit` 1 to 50). Call `read` with `path` = the top result's `path` and show the user the original file content it returns, then open the file at `<root>/<path>` so the user sees it is theirs. Re-run: rewrites `retrieval.config.json` and re-indexes only.

## Step 6: first capture and health

Ask for one short piece of knowledge worth keeping (a fact, a rule, a lesson). Propose, do not write: print the exact target path `<root>/<notes folder>/inbox/<date>-<slug>.md` and the exact text, and ask for approval. On approval write the file, re-run the `index` command from step 5, and confirm with a `search` (`mode` = `exact`) for one word from the capture. Without approval write nothing and record `step 6: capture declined <date>`.

Then run and record exit codes: `.venv/Scripts/python.exe ox_retrieval.py status --config retrieval.config.json`, and `.venv/Scripts/python.exe acceptance.py` (the sample acceptance script; it exercises the repository's own `fixtures/notes`, not the user's folder, and proves the installation, not the user's index).

Print the two habits: daily, "Capture once into `<notes folder>/inbox/`, then run `index`"; weekly, "Read the week's captures, approve what belongs in your notes, run `status`". Daily log and Friday audit are optional modules, off by default (see `identity/goals.md`).

## End of run

Print: each step as done, skipped or declined with its date; every file written with its path; every command run with its exit code; the two habit lines; and what was not verified (for example, a step whose command failed). Never report a step as done when its command failed.

# Project cabinet and Calibrate

All example business data, events and decisions in this folder are invented. The cabinet is a filing convention: one entry map per project (`PROJECT_INDEX.md`) and one compact task-and-source guide, so that every task starts from the same door, reads the authoritative source for that task, and leaves its result in a permitted dated destination. It adds navigation; it never duplicates or reorganizes the business records it points at.

The skills that operate it ship in `../skills/`: `ox-project-cabinet` builds and uses a cabinet, `calibrate` turns session lessons into operating-layer changes, and `calibrate-cabinet` repairs a cabinet after a demonstrated routing failure. The `/onboard` skill writes your first cabinet from your answers.

## Retrieval and the cabinet divide authority

Retrieval (the read-only connector in `../ox_retrieval.py`) locates material: it answers "where is the text that matches this identifier or this question". The cabinet establishes authority: it answers "which source governs this task, as of which date, and where the result belongs". Search rank is not authority, and a reachable historical copy does not repair an inaccessible authoritative source. Neither retrieval nor the cabinet grants permission to act; an order, a payment, a deletion or a configuration change needs its own authorization.

Read the project entry map, its selected guide and package identity, then the required source. Record authority, evidence coverage and date, and result destination before any authorized work. Distinguish missing, inaccessible and stale sources. Stop the affected action, record the gap, and continue only independent work.

## Start here

- [Sample project](example/PROJECT_INDEX.md): follow its selected guide, read the evidence, inspect the dated result.
- [Index template](templates/PROJECT_INDEX.md) and [task guide template](templates/task-and-source-guide.md): for an existing project keep its entry point and records; adapt these only when navigation is missing, and replace every double-braced placeholder before use. Do not add unused directories or relocate records.
- [Acceptance cases](acceptance-cases.md): eleven read-only prompts for a fresh reviewer, with the expected routes held back until scoring.

## Calibrate modes

Announce the selected mode and scope first. The first argument picks the mode; no argument means `auto`.

| Mode | Behavior | Example request |
|---|---|---|
| review | Present evidence and proposed text only; write nothing, including reports. | `Calibrate review the repeated date omission` |
| auto | Show each exact proposed change and its evidence before applying it within existing authorization and repository gates. No reply is needed when authorization already covers it. | `Calibrate auto the verified operating error` |
| full | Auto plus fresh verification, with new commands, of every durable factual claim written during the session. A self-correction calls for full; it never expands write permission. | `Calibrate full after the self-correction` |
| lite | Corrections and appends only, in an explicitly configured writable operating-memory destination; no new rules, skills or knowledge captures. If none is configured, report pending. | `Calibrate lite the configured operating memory` |

The example requests are workflow examples, not executable commands. Without an explicit mode use auto, or full after a self-correction. No scheduled or per-lookup calibration is required.

For each candidate record: the observed failure or user correction, supporting evidence and date, existing coverage, the smallest useful change, its destination, and an observable acceptance condition. Distinguish tool results from assistant assertions and from retrieved instructions. Skip duplicates, unsupported claims and one-off workarounds; repetition alone does not establish a useful standing rule.

Operating lessons describe how the agent works: route them through the maintained rules, workflow or skill review process, and regenerate generated instruction files from their source. Knowledge claims describe business facts: route them through the capture, propose and approve process; Calibrate never edits knowledge notes or business records directly. Keep only the minimum evidence, never raw transcripts, secrets or unnecessary business content.

## Cabinet correction (companion route)

A demonstrated routing failure belongs to `calibrate-cabinet`, which defaults to review. Navigation and result destinations go to the selected guide; verified authority or package selection goes to the index; access gaps go to the index's existing gap section. Business procedure changes need their own review, and cleanup needs separate authorization.

For an authorized correction: record the failing baseline task, the smallest proposed delta and the expected outcome; preserve original bytes in a unique recovery location; check for concurrent changes immediately before writing; apply only the reviewed navigation change; validate links, compare protected records, rerun the baseline and a neighboring task, and read back the changed text. A saved rule is not proof of improved behavior: fresh-session and cross-client checks stay unverified until performed.

## Not shipped in v1

`calibrate` was authored with companion agent definitions and a test-prompt set (its `agents/` and `tests/` folders). OX BrainWiki OS v1 ships the three `SKILL.md` files only; the companions are not included, and a `tests/test-prompts.md` reference inside a skill points at material that is not in this repository. No release manifest ships either: the repository commit is the package identity.

---
name: calibrate
description: Turn what this session learned about HOW the agent should work into durable operating-layer changes (CLAUDE.md rules, memory files, skills, workflows), and catch false claims the session itself wrote. Use when the user types /calibrate, at session end, after a correction or a surprise, or when the user says "save the lesson", "what did we learn", or "fix the rule". Never writes to the vault's knowledge layer.
disable-model-invocation: true
argument-hint: "[auto|full|lite|review] optional focus, e.g. 'review the worktree episode'"
metadata:
  rebuilt: 2026-09-07
  rebuilt_from: private OX BrainWiki operating notes that recorded earlier calibrate runs (not shipped)
---

Authored for One Xoluxion / OX BrainWiki; shipped with OX BrainWiki OS under the repository license.

## Codex routing

When running in Codex, route standing rules through the project's instruction-file review workflow (branch and pull request when the project requires one); if the project generates AGENTS.md or GEMINI.md from another file, change that source, never the generated output. Claude auto-memory paths are not Codex memory destinations. Use an explicitly configured writable operating-memory location only when one exists; otherwise report that candidate as pending rather than inventing a memory store. Keep the knowledge-layer and read-only memory restrictions below.

# calibrate

Calibrate reviews the session just lived and adjusts the agent's **operating layer** so the next session behaves better. It writes rules, memory, and skills. It never writes knowledge.

## Modes

The first argument picks the mode. No argument means `auto`.

- **auto** (default): find the lessons, print each proposed change to the user with its evidence, then apply. This is the "default-mode contract": nothing lands unprinted, but the run does not wait for a reply.
- **full**: same as auto, but also re-verify every factual claim the session wrote into durable files, with fresh commands, not memory. Use after long or messy sessions. If the session contained a self-correction, default to full, not auto: auto re-uses the session's own claims and cannot catch a fact that changed under it.
- **lite**: memory appends and corrections only. No new rules, no new skills, no capture. Use mid-session for one quick lesson.
- **review**: list the findings and proposed changes. Apply nothing. Use when the user wants to choose.

A second argument narrows the pass to one episode ("the backup episode", "the lock-file surprise"). Copy the block below into the reply and tick each line off as it lands.

```text
Calibrate progress:
- [ ] 1 Candidates collected, each with its evidence line
- [ ] 2 Every candidate routed to a layer, or skipped with a reason
- [ ] 3 Each change printed, then applied
- [ ] 4 Report written
- [ ] 5 Every write grepped back with a non-zero count
```

## Step 1: collect candidates

Walk the session for these signals. Each one is a candidate lesson.

- A correction from the user, or a moment the agent reversed itself.
- A claim the agent made that later evidence contradicted. These are the most valuable findings. A session that caught two of its own false claims produced the best calibrate run on record.
- A tool, command, or gate that behaved differently from what a rule or memory said.
- A workaround that took more than one attempt to find.
- A decision the user made that future sessions must respect.
- A fact another session already captured. Check before writing: search memory and `CLAUDE.md` for the lesson. If a peer session already has it in more detail, skip it and say so.

Done when every signal above has been walked and each candidate carries the evidence line that produced it.

## Step 2: route each candidate

Two layers, one question: is this about **how the agent works** or about **what the vault knows**?

- **How the agent works** goes to the operating layer, and calibrate writes it:
  - A standing rule, when the lesson generalises beyond one project: `~/.claude/CLAUDE.md` (global) or the project's `CLAUDE.md`. Put it in the existing section it belongs to. Bar is high: "nothing generalisable enough for a rule" is a normal outcome, and the lesson goes to memory instead.
  - A memory file, when the lesson is project- or machine-specific: new file, or an append to the existing one, plus its one-line entry in `MEMORY.md`. Follow the memory frontmatter format in force.
  - A skill, when the lesson is a repeatable procedure with steps. Rare. Mirror it per the skill-mirror rule.
  - A workflow or hook change, when the lesson is "the harness should do this every time".
- **What the vault knows** goes to the knowledge layer, and calibrate does NOT write it. The knowledge folder (in OX BrainWiki, for example, `01_Wiki/`) has exactly one write path: a capture in the inbox folder (`00_Raw/` in that example), a proposal, and the user's approval. Calibrate may stage **at most one** inbox capture per run when it finds durable knowledge, and it must say so. If nothing qualifies, stage nothing rather than force one.

Done when every candidate names its layer and target file, or carries a skip reason.

## Step 3: apply, with these rules

- Print every change before writing it: file, the exact text, and the evidence line that justifies it.
- Corrections keep the retraction visible. Write "RETRACTED" or "SELF-CORRECTION" next to the wrong claim with the date and the evidence, rather than deleting it. The retraction is the lesson.
- Re-read any shared file immediately before writing it, and merge into the other session's text, never over it. Another session may be writing `CLAUDE.md`, memory, or the index right now.
- Edit files directly. Memory and the global `CLAUDE.md` live outside any repo, so no commit is involved. If a change lands inside a git repo, the repo's own gates apply (attribution event, PR), and calibrate says so instead of committing.
- Never touch the knowledge folder, the operations records, or handoffs (in the OX BrainWiki example: `01_Wiki/`, `03_Operations/`). Those belong to other skills and to the capture pipeline.
- Verify after writing: grep the passage back and report the occurrence count and byte size, the same way a handoff would. If the grep returns 0 hits, the write did not land: re-read the file first (another session may have written it in between), then return to Step 3 and re-apply. Done when every change has a non-zero count.

## Step 4: report

End with a short list: each change as file, one-line summary, evidence. Then the candidates that were skipped and why (already captured, not generalisable, knowledge-layer). Then whether an inbox capture was staged. If the mode was `review`, end with the list and stop. Done when the list accounts for every candidate from Step 1, applied or skipped.

## Anti-patterns this skill exists to prevent

- Writing a "positive identification" from a single indirect signal. A lookup yields a candidate, never a holder, until a second independent check agrees.
- Saving a lesson that a sibling session already recorded better.
- Forcing a wiki node out of an operating lesson, or forcing an operating rule out of a one-off.

Tests: the companion `tests/` folder and `agents/` folder are not shipped in v1 of OX BrainWiki OS (see `cabinet/README.md`).

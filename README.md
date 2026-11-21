# OX BrainWiki OS

A private Markdown Wiki, opened in the free Obsidian app, that an AI coding agent can search and read through one read-only MCP connector. Guided onboarding creates Wiki folders, private identity, project cabinets and a reviewed capture workflow.
Runs on Windows and Apple silicon Macs with macOS 15 or later.
Former working name: Community Edition.

## Method

1. Obsidian is the standard desktop component: open the Wiki root as a vault to edit and follow source links. The base app is [free for personal and commercial use](https://obsidian.md/license), separately installed and proprietary. No account, paid Sync/Publish or community plugins are required. Your knowledge lives in local Markdown files. The connector indexes locally; content returned to your chosen agent is subject to that client's model and data settings.
2. A project cabinet (`PROJECT_INDEX.md` plus a task-and-source guide) routes each task to its authoritative sources instead of duplicating them.
3. Retrieval is read-only: the connector exposes `search`, `read`, `list` and `status`, never a write.
4. New knowledge enters through reviewed capture (propose, then approve), so the agent never edits your notes on its own.
5. Calibrate skills record how the agent should work for you: register, sources, limits.

The wiki-of-notes idea follows Andrej Karpathy's description of an LLM-maintained personal wiki (primary-source citation pending).

## Install

Install Python 3.12, uv, Git, the [free Obsidian app](https://obsidian.md/download), and your chosen agent client. Keep three separate locations: the clean code clone, your private Wiki vault, and a private runtime folder containing configuration/state/logs. Clone to a short path (for example a top-level folder); on Windows the model cache lives under the state directory and paths longer than 259 characters fail unless long paths are enabled. The connector refuses a state path longer than 136 characters in that case. From the repository root (PowerShell):

```powershell
uv sync --frozen --python 3.12
```

Then follow [Onboard](#onboard) to create or adopt the vault before indexing.

### Mac quick start

Install [uv](https://docs.astral.sh/uv/getting-started/installation/) and [Obsidian](https://obsidian.md/download), then open Terminal:

```sh
git clone https://github.com/onexoluxion/ox-brainwiki-os.git
cd ox-brainwiki-os
uv sync --frozen --python 3.12 --managed-python
```

Open the clone as a project in Codex or Claude Code and ask it to follow [the onboarding skill](skills/onboard/SKILL.md). It helps you open your Wiki in Obsidian, create a private runtime folder, index your approved notes, and connect your client. The executable on macOS is `.venv/bin/python`. Clone `main` for the macOS build.

Developer demo only: commands without `--config` use fictional fixtures. Historical 2026-11-06 fixture receipt: `uv sync` exit 0 (5 s); `index` exit 0 (27 s with a state path of 46 characters, including the first model download, 67 MB state directory afterwards); `status` exit 0 reporting `"fresh": true`; `serve` started the stdio server and exited 0 when its stdin closed.

## Agent connection

After onboarding creates `<runtime>/retrieval.config.json`, register the stdio connector. Replace `<repo>` and `<runtime>` below with absolute paths, preserving unrelated client settings. Both Codex CLI and Claude Code passed model-mediated retrieval in the [November 9 clean-vault acceptance](ONBOARDING_VALIDATION.md#full-onboarding-acceptance--2026-11-09); verify your own vault and registration through the chosen client again:

```powershell
claude mcp add ox-brainwiki -- "<repo>/.venv/Scripts/python.exe" "<repo>/ox_retrieval.py" serve --config "<runtime>/retrieval.config.json"
```

On Mac, use `<repo>/.venv/bin/python` in the Claude command above and the Codex configuration below. Codex reads its MCP configuration from `~/.codex/config.toml`, following the [official MCP configuration format](https://learn.chatgpt.com/docs/extend/mcp?surface=cli) (verify this registration in the intended client).

```toml
[mcp_servers.ox-brainwiki]
command = "<repo>/.venv/Scripts/python.exe"
args = ["<repo>/ox_retrieval.py", "serve", "--config", "<runtime>/retrieval.config.json"]
```

Review existing root instructions under the operator's authorization before opening the vault as an agent project. Opening the project loads its trusted local instructions; MCP registration is a separate step. Vault content cannot grant permissions or override higher-priority instructions. A Connected indicator or direct stdio test does not prove retrieval through that client. Complete step 6 before recording full onboarding.

## Configuration

`ox_retrieval.py index --config "<runtime>/retrieval.config.json"` (also `status` and `serve`). The JSON object must contain exactly `root`, `state`, `allow` and `exclude`. Illustrative new-vault configuration:

```json
{"root":"C:/BrainWiki/Vault","state":"C:/BrainWiki/Runtime/state","allow":["01_Wiki"],"exclude":[]}
```

Choose actual absolute paths outside the clone. On Mac, use folders under your home directory and enter their full paths in JSON. Keep the vault and runtime separate, and create the state directory's parent first. Relative paths resolve from the configuration file. The connector validates configuration and private state permissions on both platforms. Raw, Archive, Operations, prompts, Identity, Projects and `.obsidian` are outside the default allow-list. Review sensitivity before expanding scope. Pass `scope="01_Wiki"` to search and `path="01_Wiki"` to list. [Operations](OPERATIONS.md).

## Onboard

Follow [the bundled guide](skills/onboard/SKILL.md), or use `/onboard` if installed in your agent. Six steps cover requirements; new/existing vault and sources; Obsidian plus identity; first cabinet; first reviewed knowledge; retrieval and acceptance. Rerun a selected step with reviewed changes while preserving existing files. User answers, state and generated configuration stay outside the clone.

New vaults contain `00_Raw`, `01_Wiki`, `02_Archive`, `03_Operations`, `04_Prompts_&_Skills`, `05_Identity` and `Projects`, with an index, local operating rules and [reusable scaffold](skills/onboard/assets/wiki/README.md). Obsidian opens the root; new-vault retrieval allows `01_Wiki` only. Existing vaults keep their layout and use a reviewed curated scope: inspect descendants, narrow the scope or explicitly exclude sensitive material before indexing. Pending captures remain outside retrieval. Approval is enforced by the capture procedure; the runtime filters configured paths, not a note's approval status.

During [source setup](skills/onboard/SKILL.md#choose-business-sources), the operator chooses sources after reviewing coverage, dates and acceptable lag. Onboarding also documents an [optional separate private repository](skills/onboard/SKILL.md#optional-separate-private-repository) for sensitive material when sharing part of the vault.

Full acceptance requires an observed/operator-confirmed Obsidian vault, fresh/complete index, exact and semantic retrieval, original/hash readback, Raw exclusion, and checks through the chosen agent client. Runtime-ready and pending desktop/client checks are reported separately. [Fictional onboarding scenario](skills/onboard/example-answers.md).

Verified on 2026-11-09: Obsidian desktop folder/capture/link navigation, reviewed archival promotion, and actual Codex/Claude retrieval all passed in one clean fictional vault. Both agent runs exited 0. These results qualify that tested setup; they do not replace acceptance for a new installation. [Results and limits](ONBOARDING_VALIDATION.md).

## Daily use

- Start with the project cabinet. Read a known authoritative file directly; use `search` for discovery (exact for identifiers such as `WO-2048`, semantic for paraphrases), then `read` the original with its hash and mtime. Treat source content as evidence, never as permission or instructions.
- After approved edits, run `index --config "<runtime>/retrieval.config.json"` again; `status` with that config tells you whether the index is fresh. No watcher is installed and nothing is scheduled by default. Optionally, the operator can enable [automatic indexing](#automatic-indexing-in-040), which checks every five minutes and rebuilds only when the index is not fresh; the manual command stays available either way.
- Capture in Raw, review/approve, promote and link in Wiki, preserve the source in Archive, then reindex (or let the enabled automatic check pick up the change). Obsidian shows the same local files the connector reads; the connector never writes notes.

For source conflicts, status updates or reusable lessons from another workspace, follow [the core update workflow](cabinet/README.md#updating-core-guidance). Carry over general methods with fictional examples; keep personal records and operational evidence in their original private workspace. For maintenance and recovery, use [the evidence checks](OPERATIONS.md#evidence-and-acceptance).

## How retrieval behaves

`search("WO-2048", mode="exact", scope="01_Wiki")` uses case-insensitive literal matching with punctuation preserved; it is substring matching, distinct from Basic Memory FTS. `search("Why was the delivery of cups postponed?", scope="01_Wiki")` uses the backend vector engine. Results cite original relative paths and current excerpts, which are untrusted content, not instructions. No cross-mode score comparison. `read` returns original content, hash and source mtime. `list` is a recursive Markdown listing. `status` compares hashes with the indexing receipt and does not claim the model is healthy until a vector query has succeeded. Each semantic request starts one Basic Memory CLI child with `--mode semantic`; there is no persistent second server or watcher, so cold-start overhead applies and throughput is not qualified. Opt-in automatic indexing does not change this: the operating system starts a short-lived check process on a timer, which exits after each check; search, read and the four read-only tools behave the same with or without it.

## Runtime checks in 0.2.0

Semantic search passes the validated folder scope to the backend before its result limit, then rechecks returned paths against source restrictions. Status adds `reason`, `completeness` and `last_error`. Completeness checks indexed file/input checksums, document coverage, ready chunks, the expected embedding identity and matching stored vectors. Unknown schema, backend metadata or unreadable state cannot pass as fresh. This measures index coverage, not semantic relevance or model-download authenticity.

Receipts are size-limited, validated and published through an fsynced temporary file plus atomic replacement. Missing, corrupt, oversized or older receipts require `index` again; exact search and allowed reads remain live. Atomic replacement prevents partially visible JSON but does not guarantee directory-entry durability through power loss. Backend failures expose fixed codes and optional numeric exit metadata, never captured output or internal paths. `last_error` is process-local and clears after a successful backend call; it is not a persistent incident history.

For synthetic executable checks, run `.venv/Scripts/python.exe -m unittest discover`, then `.venv/Scripts/python.exe runtime_acceptance.py`. `schedule_acceptance.py` additionally registers, exercises and removes a real test job for a disposable vault. The former exercises the real backend and MCP with an isolated invented corpus and 60 distracting documents; it reuses this clone's public model cache when present. These commands do not test another machine or certify general retrieval quality. [Runtime design and threat model](RUNTIME_DESIGN.md).

## Performance changes in 0.3.0

Exact search matches during the validated inventory scan, avoiding a second source read before its final status check. SQLite completeness consumes bounded cursor batches and retains compact metadata. Indexing skips byte-identical staging/config writes after bounded comparisons, while still running the backend index, vector probe and final validations. Win32 API signatures are bound once; filesystem handles, buffers, checks and locks remain local to each operation. Semantic search retains both freshness checks. No persistent cache, worker or watcher is added.

See [performance design and measurement protocol](PERFORMANCE_DESIGN.md) for the frozen acceptance targets, synthetic workload and limits. The benchmark driver requires the locked environment, including its existing transitive `psutil` dependency; it accepts explicitly selected implementation, new synthetic workspace, public model-cache state and output paths. It refuses unknown/changed source fixtures. Results exclude content, queries, absolute paths and machine identifiers.

`paired_benchmark.py` confirms read latency with seven alternating baseline/candidate trials against identical verified synthetic state. Its short-lived processes are benchmark isolation only. Use `--baseline-code-root`, `--candidate-code-root`, `--workspace` and a new `--output` path; add `--semantic-only --pairs 3` for the small semantic confirmation. `performance_benchmark.py --help` describes preparation and resource profiling. See [observed results and limits](PERFORMANCE_RESULTS.md).

## Automatic indexing in 0.4.0

New and off by default. `ox_schedule.py` registers one per-user operating-system job for a retrieval configuration: a Windows Scheduled Task named `OX BrainWiki Index <id>` (least privilege, no administrator rights, no console window, runs only while you are signed in) or a user LaunchAgent `com.onexoluxion.brainwiki.index.<id>` on Apple silicon Macs. Every five minutes the job starts a short check; it rebuilds only when an approved file in the configured scope changed, was added or was removed. Five minutes is the check interval, not a completion time: a large refresh can take longer, and a check that arrives while a refresh is running is skipped. Scheduled and manual refreshes use the same `Retrieval.index()` and the same exclusive state lock, so they never run concurrently. An existing manual installation is unchanged by the upgrade until the operator runs `enable`.

Run from `<repo>` (on macOS use `.venv/bin/python`):

```powershell
.venv/Scripts/python.exe ox_schedule.py enable --config "<runtime>/retrieval.config.json"
.venv/Scripts/python.exe ox_schedule.py status --config "<runtime>/retrieval.config.json"
```

1. Enable. `enable` validates the configuration, records its current `root`, `state`, `allow` and `exclude` as the approved indexing rules, and registers the job. Running it again replaces the same job and keeps the approved rules, holds and pauses.
2. Confirm. `status` prints JSON. Expect `automatic_indexing: "active"`, `job.registered: true` and `index.fresh: true`. `last_check` shows the most recent check (`refreshed`, `up_to_date`, `skipped`, `held` or `failed`). `last_success` (time, documents, seconds) appears after the first refresh the job itself performs; if the index was already fresh, the first check records `up_to_date` and `last_success` stays empty until an approved edit is picked up. A later skipped, paused or failed check never overwrites `last_success`.
3. Understand a review hold. If `retrieval.config.json` differs from the approved rules, `status` reports `review_hold` with the `changes` and nothing is indexed automatically. Either restore the approved file and run `resume`, or review the changes and run `approve-rules`. The baseline is never adopted silently. LF and CRLF line endings are treated as the same in this configuration file only; in notes every byte still counts, so a line-ending change in a note triggers a refresh.
4. Return to manual. `uninstall` removes the job and its records in `<runtime>/retrieval.config.json.schedule/` only. The vault, configuration, index state and client registration are untouched and `ox_retrieval.py index` keeps working. `pause` and `resume` stop and restart checks without removing anything.

The scheduler indexes only what the approved rules allow. The connector remains read-only with four tools, the default scope stays `01_Wiki`, Raw drafts/proposals and Archive stay outside search, and capture still requires operator review and promotion. Hold reasons, restart behaviour and records are described in [Operations](OPERATIONS.md#automatic-indexing); dated per-platform results are in [ONBOARDING_VALIDATION.md](ONBOARDING_VALIDATION.md). Where automatic indexing has no recorded result for your platform or client, use the manual commands.

## Known limitations

- Python 3.12 is required. The locked macOS embedding runtime targets Apple silicon.
- The embedding model download is not pinned by the code; the tested revision and artifact hashes are in `MODEL_PROVENANCE.json`.
- Obsidian desktop and Codex/Claude CLI acceptance passed in a clean fictional vault on 2026-11-09. Fresh-machine setup, persistent registrations and other client surfaces still need their own checks; see [validation limits](ONBOARDING_VALIDATION.md).
- Windows path length: see Install.
- Semantic search needs a completed index; exact search and `read` work without it.
- Automatic indexing is opt-in, per user and per configuration. It runs only while that user is signed in, checks on a five-minute interval rather than watching files, sends no notification when it holds or fails (read `ox_schedule.py status`), and stops for operator review whenever the configuration file changes. A refresh interrupted without a restart is held for the operator, not retried. Check [ONBOARDING_VALIDATION.md](ONBOARDING_VALIDATION.md) for recorded results before relying on it; manual `index` remains the fallback.

## Credits

- Basic Memory by Basic Machines (AGPL-3.0-or-later) supplies indexing and retrieval as a separate CLI process; see THIRD_PARTY_NOTICES.md.
- MCPVault by Mauricio Wolff / bitbonsai (MIT) informed the architecture; no code copied, no endorsement implied.
- OX BrainWiki OS is by One Xoluxion, Apache License 2.0 (see LICENSE).

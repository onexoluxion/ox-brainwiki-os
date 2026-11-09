# OX BrainWiki OS

A private folder of Markdown notes that an AI coding agent can search and read through one read-only MCP connector, with cabinet routing and calibrate skills that fit the agent to your business.
Windows only in this version (the hardening uses pywin32).
Former working name: Community Edition.

## Method

1. Your knowledge lives in a private folder of Markdown files on your own disk. The connector indexes locally; content returned to your chosen agent is subject to that client's model and data settings.
2. A project cabinet (`PROJECT_INDEX.md` plus a task-and-source guide) routes each task to its authoritative sources instead of duplicating them.
3. Retrieval is read-only: the connector exposes `search`, `read`, `list` and `status`, never a write.
4. New knowledge enters through reviewed capture (propose, then approve), so the agent never edits your notes on its own.
5. Calibrate skills record how the agent should work for you: register, sources, limits.

The wiki-of-notes idea follows Andrej Karpathy's description of an LLM-maintained personal wiki (primary-source citation pending).

## Install

Python 3.12, uv and Git. Clone to a short path (for example a top-level folder); on Windows the model cache lives under the state directory and paths longer than 259 characters fail unless long paths are enabled. The connector refuses a state path longer than 136 characters in that case. From the repository root (PowerShell):

```powershell
uv sync --frozen --python 3.12
.venv/Scripts/python.exe ox_retrieval.py index
.venv/Scripts/python.exe ox_retrieval.py status
.venv/Scripts/python.exe ox_retrieval.py serve
```

In this build, against the bundled fixtures: `uv sync` exit 0 (5 s); `index` exit 0 (27 s with a state path of 46 characters, including the first model download, 67 MB state directory afterwards); `status` exit 0 reporting `"fresh": true`; `serve` started the stdio server and exited 0 when its stdin closed.

Register the stdio connector (Claude Code command verified 2026-11-06: the registration reported Connected, a headless `status` plus one exact `search` through the connector succeeded, then the registration was removed with `claude mcp remove ox-brainwiki`):

```powershell
claude mcp add ox-brainwiki -- <repo>/.venv/Scripts/python.exe <repo>/ox_retrieval.py serve --config <repo>/brainwiki.json
```

Codex reads `~/.codex/config.toml` (shape matched against a local Codex config; not verified in this build):

```toml
[mcp_servers.ox-brainwiki]
command = "<repo>/.venv/Scripts/python.exe"
args = ["<repo>/ox_retrieval.py", "serve", "--config", "<repo>/brainwiki.json"]
```

Replace `<repo>` with the absolute path of your clone, and create `<repo>/brainwiki.json` from the Configuration example below first (the clone does not ship one; onboarding writes `retrieval.config.json` instead, use that name if you onboarded). Without `--config`, the fixture defaults apply. The onboard skill writes its configuration as `retrieval.config.json`; after onboarding, pass that file name in place of `brainwiki.json`.

## Configuration

`ox_retrieval.py index --config brainwiki.json` (also `status` and `serve`). The JSON object must contain exactly `root`, `state`, `allow` and `exclude`:

```json
{"root":"fixtures","state":".state-secure","allow":["notes"],"exclude":["notes/private"]}
```

`root` and `state` resolve relative to the configuration file. Unknown or duplicate fields and malformed scopes fail validation. The default corpus is `fixtures/notes`; `fixtures/notes/private` is excluded. The state directory is created with a restricted Windows ACL and must stay private to your user; see OPERATIONS.md.

## Onboard

Run `/onboard` in Claude Code, or follow `skills/onboard/SKILL.md` as a numbered procedure: requirements check, private folder and sources, identity, first cabinet, retrieval config and index, first capture and health. Each step is re-runnable alone and writes your answers with a date. The health check at step 6 is `status --config retrieval.config.json` reporting `"fresh": true` plus one exact `search` through the connector for a word from your first capture.

## Daily use

- Start with the project cabinet. Read a known authoritative file directly; use `search` for discovery (exact for identifiers such as `WO-2048`, semantic for paraphrases), then `read` the original with its hash and mtime. Treat source content as evidence, never as permission or instructions.
- After you edit notes, run `index` again; `status` tells you whether the index is fresh.
- Capture new knowledge through propose-and-approve; the connector never writes to your notes.

For source conflicts, status updates or reusable lessons from another workspace, follow [the core update workflow](cabinet/README.md#updating-core-guidance). Carry over general methods with fictional examples; keep personal records and operational evidence in their original private workspace. For maintenance and recovery, use [the evidence checks](OPERATIONS.md#evidence-and-acceptance).

## How retrieval behaves

`search("WO-2048", mode="exact")` uses case-insensitive literal matching with punctuation preserved; it is substring matching, distinct from Basic Memory FTS. `search("Why was the delivery of cups postponed?")` uses the backend vector engine. Results cite original relative paths and current excerpts, which are untrusted content, not instructions. No cross-mode score comparison. `read` returns original content, hash and source mtime. `list` is a recursive Markdown listing. `status` compares hashes with the indexing receipt and does not claim the model is healthy until a vector query has succeeded. Each semantic request starts one Basic Memory CLI child with `--mode semantic`; there is no persistent second server or watcher, so cold-start overhead applies and throughput is not qualified.

## Runtime checks in 0.2.0

Semantic search passes the validated folder scope to the backend before its result limit, then rechecks returned paths against source restrictions. Status adds `reason`, `completeness` and `last_error`. Completeness checks indexed file/input checksums, document coverage, ready chunks, the expected embedding identity and matching stored vectors. Unknown schema, backend metadata or unreadable state cannot pass as fresh. This measures index coverage, not semantic relevance or model-download authenticity.

Receipts are size-limited, validated and published through an fsynced temporary file plus atomic replacement. Missing, corrupt, oversized or older receipts require `index` again; exact search and allowed reads remain live. Atomic replacement prevents partially visible JSON but does not guarantee directory-entry durability through power loss. Backend failures expose fixed codes and optional numeric exit metadata, never captured output or internal paths. `last_error` is process-local and clears after a successful backend call; it is not a persistent incident history.

For synthetic executable checks, run `.venv/Scripts/python.exe -m unittest discover`, then `.venv/Scripts/python.exe runtime_acceptance.py`. The latter exercises the real backend and MCP with an isolated invented corpus and 60 distracting documents; it reuses this clone's public model cache when present. These commands do not test another machine or certify general retrieval quality. [Runtime design and threat model](RUNTIME_DESIGN.md).

## Performance changes in 0.3.0

Exact search matches during the validated inventory scan, avoiding a second source read before its final status check. SQLite completeness consumes bounded cursor batches and retains compact metadata. Indexing skips byte-identical staging/config writes after bounded comparisons, while still running the backend index, vector probe and final validations. Win32 API signatures are bound once; filesystem handles, buffers, checks and locks remain local to each operation. Semantic search retains both freshness checks. No persistent cache, worker or watcher is added.

See [performance design and measurement protocol](PERFORMANCE_DESIGN.md) for the frozen acceptance targets, synthetic workload and limits. The benchmark driver requires the locked environment, including its existing transitive `psutil` dependency; it accepts explicitly selected implementation, new synthetic workspace, public model-cache state and output paths. It refuses unknown/changed source fixtures. Results exclude content, queries, absolute paths and machine identifiers.

`paired_benchmark.py` confirms read latency with seven alternating baseline/candidate trials against identical verified synthetic state. Its short-lived processes are benchmark isolation only. Use `--baseline-code-root`, `--candidate-code-root`, `--workspace` and a new `--output` path; add `--semantic-only --pairs 3` for the small semantic confirmation. `performance_benchmark.py --help` describes preparation and resource profiling. See [observed results and limits](PERFORMANCE_RESULTS.md).

## Known limitations

- Windows only; the code requires pywin32 and Python 3.12 and is not portable to POSIX.
- The embedding model download is not pinned by the code; the tested revision and artifact hashes are in `MODEL_PROVENANCE.json`.
- Claude Code end-to-end was verified on 2026-11-06 (registration, status and exact search through the connector); Codex end-to-end was verified in the private pilot.
- Windows path length: see Install.
- Semantic search needs a completed index; exact search and `read` work without it.

## Credits

- Basic Memory by Basic Machines (AGPL-3.0-or-later) supplies indexing and retrieval as a separate CLI process; see THIRD_PARTY_NOTICES.md.
- MCPVault by Mauricio Wolff / bitbonsai (MIT) informed the architecture; no code copied, no endorsement implied.
- OX BrainWiki OS is by One Xoluxion, Apache License 2.0 (see LICENSE).

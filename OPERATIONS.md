# Operations

Run index manually after source edits, or enable the opt-in [automatic indexing](#automatic-indexing) job, which calls the same index under the same lock. There is no watcher, and no schedule exists until the operator enables one. Index filters before copying, removes deleted staged Markdown, then calls `basic-memory project index main`. Basic Memory writes only staging and its isolated .state-secure/bm database. Model downloads and cache are under .state-secure; initial installation/download needs network. Inference is local FastEmbed bge-small-en-v1.5. Full dependency footprint is 161 installed packages, pinned transitively in uv.lock. Do not interpret this as a small extracted engine.

Operations serialize through an exclusive Windows state-file lock. Concurrent processes receive a sharing failure rather than reading a rebuilding index. The state directory must have a restricted DACL allowing only the current user, SYSTEM and Administrators; newly created state is restricted at creation. Existing broadly accessible state is rejected, never silently chmodded or adopted. Choose a new state path for migration. The selected state parent must exist. Ancestors are pinned against rename while the lock is held; preexisting linked state is rejected. Same-user malicious processes and administrators are outside the local account isolation boundary.

On macOS, use an ordinary local folder under your home directory for the runtime. The connector creates owner-only state and takes an exclusive nonblocking lock. It refuses shared state, ACL grants along the state path, untrusted ancestors, and linked state entries. It opens source files without following links and verifies the opened file before reading. Existing state permissions need to meet these checks. The backend runs with private home and cache directories under state and its process group is cleaned up on exit or failure.

Rebuilds clear the receipt before changing staging and publish it only after successful backend indexing, stable source hashes and a vector probe. Failure leaves semantic retrieval unavailable until a successful rebuild. This avoids maintaining multiple full index copies. Do not change production source ACLs as part of setup; the reader protects against traversal and source-directory substitution using handle checks/pins.

A missing receipt, source change or failed index prevents semantic retrieval. Exact search and reads remain live. Subprocess failures have fixed reason codes for startup, runtime, cleanup, timeout, output limit, invalid output and nonzero exit. Status exposes only bounded metadata in `last_error`; raw backend output is not returned. Basic Memory may keep its own isolated logs. A model failure never falls back to lexical search under semantic mode. Status does not actively probe the model. Index success includes a vector probe and fingerprints of source inventory, database, configuration, dependency versions and model artifacts, plus read-only per-document/vector completeness checks; this is not general query-quality certification.

Version 0.2.0 receipts use schema 1. Existing receipts from 0.1.0 are invalidated evidence: run the ordinary manual `index` command once, with the intended config. No source migration, ACL rewrite or automatic repair occurs. The completeness adapter is deliberately limited to pinned Basic Memory 1.0.0, SQLite/sqlite-vec and the packaged embedding identity. A backend/schema change must receive its own adapter review; unknown remains not fresh. Checks have document/chunk/field limits and a SQLite work deadline, use the existing exclusive guard, and return counts without document names or text. The backend's sync checksum permits expected staged-frontmatter normalization while the source remains unchanged.

Artifact identity also refuses more than 1,000 model-tree entries, 100 selected model files, 256 MiB in one artifact or 512 MiB across selected artifacts. Such state cannot be marked fresh; the runtime does not delete it or raise limits automatically. Receipts are unsigned evidence under operator-owned state permissions, not authentication against someone who can rewrite both the database and receipt.

## Configuration

The `state` path's parent directory must exist before `index`, `status` or `serve` runs: retrieval pins that parent while the lock is held and creates only the state directory itself (new onboarding keeps configuration, state and logs in a separate private runtime folder outside both vault and clone). On Windows, the model cache lives under the state directory, and Windows refuses paths longer than 259 characters while long paths are disabled; the connector therefore refuses a state path longer than 136 characters (259 minus the model cache suffix) unless `LongPathsEnabled` is set, with the message `state path too long for Windows: <N> characters, limit 136; use a shorter install or state path, or enable Windows long paths (LongPathsEnabled)`. Recommended install path: a short top-level folder (the timing in README.md was measured with a 46-character state path).

`acceptance.py` is a developer check: it indexes and queries the repository's own `fixtures/notes` into the default state directory (`.state-secure`) and is not part of onboarding; [current onboarding](skills/onboard/SKILL.md) uses `status --config "<runtime>/retrieval.config.json"`, requiring `fresh: true` and complete coverage, exact and semantic searches with the actual curated scope, original/hash readback, and exclusion of Raw. Full onboarding also verifies the vault in Obsidian and retrieval through the chosen agent client. Direct stdio proof alone leaves client verification pending.

Recovery: stop the connector, preserve the failed state privately and select a new unused state path in the config, rerun index, then run `status`, exact and semantic searches and original readback through the intended client with the same explicit configuration and curated scope. If automatic indexing is enabled, the edited configuration no longer matches the approved rules and checks stop in `review_hold` until the operator runs `approve-rules`. Source notes are never changed by indexing; rollback means stop using this connector. Do not remove source data. Keep source data and failed state separate and private, and do not publish state. The state directory contains staged notes and vectors and must remain private to the account running the connector.

Initial candidate evidence, recorded 2026-11-06: boundary review, remote scan, clean locked installation, private-corpus acceptance and actual Codex client checks were reported for the versions named in RELEASE_CHECKLIST.md. In the pilot, Claude model-mediated acceptance was blocked by that environment's API authentication (401); on 2026-11-06 Claude Code registration, `status` and one exact `search` through the connector were verified. These dated receipts do not certify later revisions, the current user's installation or newly added acceptance cases. Full replacement of an existing retrieval setup requires checks in its intended clients and routine-work quality/latency evidence. Immutable model-download pinning and model redistribution remain open; see MODEL_PROVENANCE.json and THIRD_PARTY_NOTICES.md.

Release gates: cabinet templates and synthetic routing acceptance, reviewed portable Calibrate rights/security and mode tests, primary-source attribution for the Karpathy foundation, package/license/private-data audit, claimed-platform tests. These were deliberately not substituted with copied private skills.

## Evidence and acceptance

[November 9 clean-vault acceptance](ONBOARDING_VALIDATION.md#full-onboarding-acceptance--2026-11-09) verified Obsidian desktop navigation and actual Codex/Claude retrieval. Both agent runs exited 0; final index/status were fresh and complete. The test also confirmed stale-state refusal after Obsidian normalized line endings, followed by successful reindex recovery. Finish desktop saves before final indexing. These are dated results for one tested setup, not a fresh-machine or persistent-registration claim.

Keep a dated receipt for the exact version and destination being checked. Record the command or tool, exit code or error, inputs covered, observed result and remaining gaps. A process running or a connector reporting Connected establishes availability only. Read the complete result before claiming success: a failed batch can leave valid partial work, and a successful local change can still be absent from another client or destination.

| Claim | Evidence required |
|---|---|
| Sources are current | Source inventory matches the receipt; source dates cover the question. A file's checkout time is not its evidence date. |
| Retrieval works for a task | An exact identifier and a paraphrased question return the expected allowed source; read back the original and check its scope/date. A fresh index alone is not query-quality evidence. |
| A repair is installed | The installed version or hash matches the reviewed change, followed by a successful operation through the intended client. An isolated test is evidence for that test environment only. |
| Recovery works | Restore source/configuration backups into a separate private location with unused state, rebuild, then check source hashes, expected retrieval, exclusions and read-only behavior. State explicitly what was not restored. |
| A recurring process is reliable | Dated receipts from actual unattended runs and an observed failure-notification path, if a schedule is configured. Manual runs do not count as unattended runs. Nothing is scheduled by default. When the opt-in [automatic indexing](#automatic-indexing) job is enabled, its own records (`last_check`, `last_success`, `history.jsonl`) are the receipts for index refreshes on that installation; it sends no notification, so a hold or failure is seen only by reading `ox_schedule.py status`. Any other recurring work is configured and evidenced separately. |
| Retrieval improved | Comparable before/after corpus versions, held-out questions, configuration and scoring. If a baseline is unavailable, record a new baseline without claiming improvement. |

Before maintenance, inspect the last receipt and any active owner; avoid competing rebuilds. If automatic indexing is enabled, `pause` it for the maintenance and `resume` afterwards. Preserve failed state and logs privately. Reconcile source and destination receipts before retrying or marking work complete. Keep recovery copies until separately authorized cleanup; never delete a lock or weaken access checks to force progress. The recovery and acceptance steps above are procedures, not claims that these checks have run on a user's installation.

## Obsidian and capture

Obsidian is the standard free desktop component and opens the vault root. It sees all the vault's folders; new-vault onboarding allows `01_Wiki/` only. Raw/proposals, Archive, Operations, prompts, Identity, Projects and `.obsidian/` remain outside that default scope. Existing vaults keep their layout: inspect custom curated folders and their descendants, narrowing or excluding sensitive content before indexing. Approval is a capture-process boundary; the runtime indexes configured paths without interpreting approval labels. Source archive links work in Obsidian without indexing archived material.

After approval, promote/link knowledge, preserve the source bytes at a new archive path, then reindex manually with the external configuration, or let the next automatic check rebuild if the operator enabled [automatic indexing](#automatic-indexing). Preserve existing archive entries. Obsidian follows local file changes, but the retrieval index has no watcher: without the opt-in job nothing refreshes it, and with the job a change is picked up at the next five-minute check, not at save time. Moving or renaming the vault requires updating the external config, client registration if its config path changes, and rebuilding/verifying before reuse; with automatic indexing enabled, that configuration edit also needs `approve-rules`. Back up original notes, provenance and configuration privately; a rebuilt index is not a source backup. Sync, Publish, accounts and community plugins are optional.

## Automatic indexing

Opt-in, new in runtime 0.4.0, off until the operator runs `enable`. An existing manual installation is unaffected by the upgrade. Supported on Windows and on Apple silicon Macs with macOS 15 or later. Dated per-platform and per-client results are recorded in [ONBOARDING_VALIDATION.md](ONBOARDING_VALIDATION.md); where no result is recorded for a platform or client, treat automatic indexing as unverified there and keep using the manual `index` command, which stays available and unchanged in every case.

### Commands

Run from `<repo>` with the same configuration used for manual indexing (macOS: `.venv/bin/python`):

```powershell
.venv/Scripts/python.exe ox_schedule.py enable        --config "<runtime>/retrieval.config.json"
.venv/Scripts/python.exe ox_schedule.py status        --config "<runtime>/retrieval.config.json"
.venv/Scripts/python.exe ox_schedule.py pause         --config "<runtime>/retrieval.config.json"
.venv/Scripts/python.exe ox_schedule.py resume        --config "<runtime>/retrieval.config.json"
.venv/Scripts/python.exe ox_schedule.py approve-rules --config "<runtime>/retrieval.config.json"
.venv/Scripts/python.exe ox_schedule.py uninstall     --config "<runtime>/retrieval.config.json"
```

| Command | Effect |
|---|---|
| `enable` | Validates the configuration as the indexer does, records its digest and parsed rules as the approved baseline, and registers one per-user job: a Windows Scheduled Task `OX BrainWiki Index <id>` (interactive token, least privilege, no administrator rights, no console window, runs only while the user is signed in) or a user LaunchAgent `com.onexoluxion.brainwiki.index.<id>`. `<id>` is derived from the configuration path. Running `enable` again replaces the same job, never adds a second one, and keeps the approved baseline, holds and pauses. |
| `status` | Prints the JSON described below. It records no hold and changes no schedule record. |
| `pause` | Records a `manual_pause` hold. The job stays registered; each check records `held` and indexes nothing. |
| `resume` | Clears the current hold and any leftover run record so the next check proceeds. For a `rules_changed` hold it clears only if the file again matches the approved baseline; otherwise it prints `resumed: false` and exits 2. |
| `approve-rules` | Records the current configuration as the new approved baseline, prints the `approved_changes`, and clears a `rules_changed` hold. Other holds are left in place. |
| `uninstall` | Removes the job and the schedule records. See [Uninstall and rollback](#uninstall-and-rollback). |
| `run` | The entry the job calls. An operator can run it for one immediate check. Exit 0 for `refreshed` or `up_to_date`, 2 for `skipped`, `held` or not enabled, 1 for `failed`. |

The job embeds the absolute paths of the interpreter, `ox_schedule.py` and the configuration. Before moving or renaming the clone, the runtime folder or the configuration file, run `uninstall`; run `enable` again at the new location.

### Checks and refreshes

Every five minutes the job starts one check, which exits when done; no process stays resident. A check compares the configuration with the approved baseline, takes the exclusive state lock, and reads index status. If the index is fresh it records `up_to_date`. If an approved file in the configured scope changed, was added or was removed, it runs the same `Retrieval.index()` as `ox_retrieval.py index` and records `refreshed`. Five minutes is the check interval, not a completion time: a large refresh can take longer, and a check that arrives while a refresh is running is skipped. On Windows the task stops a run that exceeds one hour; a refresh stopped that way is treated as an interruption (below).

Scheduled and manual indexing never run concurrently. Whichever holds the state lock proceeds; a scheduled check that finds the lock held by a manual `index`, a `status` or a search records `skipped` with reason `writer_busy` and tries again at the next check, and a manual command that meets a running scheduled refresh receives the usual sharing failure. Two more conditions are skipped and retried without a hold: `source_changing` (a file was saved while the refresh was running) and `source_unavailable` (the source or state could not be read at that moment).

### Status

`status` prints these fields:

| Field | Meaning |
|---|---|
| `automatic_indexing` | `not_enabled`: no schedule recorded for this configuration. `active`: job registered, no hold. `paused`: `manual_pause` hold. `review_hold`: `rules_changed` hold. `held`: any other hold. `in_progress`: the state lock was held by another operation when `status` ran, normally a refresh; `index` is empty in that reading. `job_missing`: the schedule is recorded and not held, but the operating-system job is not registered; run `enable` again. |
| `job` | `name`, `registered` and `check_interval_seconds`. |
| `last_check` | The most recent check: `outcome` (`refreshed`, `up_to_date`, `skipped`, `held`, `failed`), `reason` and time. |
| `last_success` | The most recent refresh the job completed: time, `documents`, `seconds` and trigger. Kept separately from `last_check`, so a later skipped, held or failed check never overwrites it. Empty until the job has performed a refresh; an `up_to_date` check does not set it. |
| `hold` | Empty, or `reason`, `since`, a `resolve` instruction and, for rule changes, a `changes` diff of `root`, `state`, `allow` and `exclude`. |
| `index` | `fresh`, `reason` and `indexed_at` from the same status check the manual command uses. |

`status` reports a rule change as soon as it reads the file, even before the next check has recorded the hold. A healthy enabled installation shows `automatic_indexing: "active"`, `job.registered: true` and `index.fresh: true`.

### Indexing rules and review hold

The indexing rules are the retrieval configuration file: `root`, `state`, `allow` and `exclude`. `enable` is the operator's approval of that file as it stands. Every check compares the file with the approved baseline. LF and CRLF line endings are treated as the same in this rule file only; every other byte matters, including whitespace and key order. Any other difference, or an unreadable file, places the writer in `review_hold` with reason `rules_changed`, and nothing is indexed automatically until the operator does one of two things:

- restores the approved file and runs `resume`, or
- reviews the `changes` shown by `status` and runs `approve-rules`.

When the parsed rules are identical and only formatting differs, `changes` says so. The baseline is never adopted silently. Business notes keep the existing byte-exact freshness check: an LF/CRLF change in a note still counts as a change and triggers a refresh.

### Holds

A hold is a file, so it persists across restarts and sign-outs. While a hold exists every check records `held` and exits. The first hold is the one kept; a later condition does not replace it.

| Reason | Cause | Resolution |
|---|---|---|
| `manual_pause` | The operator ran `pause`. | `resume`. |
| `rules_changed` | The configuration differs from the approved baseline. | Restore the file and `resume`, or review `changes` and `approve-rules`. |
| `run_failed` | A refresh, or its configuration/state validation, failed with a fixed code (recorded as the hold detail and as the `failed` check reason). | Run `ox_retrieval.py index --config ...` manually to see the error, fix the cause, then `resume`. |
| `interrupted` | A refresh stopped without a result and no restart explains it. | Run `ox_retrieval.py status --config ...` to inspect the state, then `resume`; the next check rebuilds. |
| `record_unreadable` | A schedule record could not be read. | Inspect the schedule folder, then `resume`. If `schedule.json` itself is damaged, `uninstall`, review the configuration, and `enable` again. |

### Restart behaviour

After a restart and sign-in the job resumes its normal schedule; nothing needs to be re-enabled. Each refresh writes a run record containing the boot time before it starts and removes it when it finishes. A check that finds a leftover run record retries the refresh automatically only when the record shows the run began before the current boot, that is, a restart interrupted it. An interruption within the same boot holds as `interrupted` for the operator: a killed process, a sign-out, the Windows one-hour task limit, or a Windows Fast Startup shutdown, which does not reset the boot time. Manual pauses, rule-review holds and failures are never cleared by a restart.

### Records

Records live in a private folder beside the configuration: `<runtime>/retrieval.config.json.schedule/`, created with the same owner-only protection as state.

| File | Contents |
|---|---|
| `schedule.json` | Approved rule digest and parsed rules, enable/approval times |
| `hold.json` | Current hold, if any |
| `run.json` | Present only while a refresh is running or after one was interrupted |
| `last.json` | Most recent check |
| `success.json` | Most recent completed refresh |
| `history.jsonl` | The most recent 200 checks |
| `job.xml` (Windows) | Job definition |

They hold codes, timestamps and the approved rules only, never note content. The approved rules include the absolute `root` and `state` paths, so keep the folder private and out of shared receipts. AI clients are unaffected: the connector remains read-only with four tools, the default scope stays `01_Wiki`, Raw drafts/proposals and Archive stay outside search, and the capture workflow is unchanged. The scheduler indexes only what the approved rules allow.

## Uninstall and rollback

To return to manual indexing only, run step 1 and stop: the vault, `retrieval.config.json`, state/index and client registration are untouched, and `ox_retrieval.py index` continues to work.

1. If automatic indexing was enabled, remove it first, while the clone and configuration still exist: `.venv/Scripts/python.exe ox_schedule.py uninstall --config "<runtime>/retrieval.config.json"` from `<repo>`. This removes the operating-system job and the records in `<runtime>/retrieval.config.json.schedule/`; unexpected extra files in that folder are left for inspection. `status` should then report `not_enabled` and `job.registered: false`.
2. Remove the connector registration: `claude mcp remove ox-brainwiki` in Claude Code (usage read from `claude mcp remove --help`), or delete the `[mcp_servers.ox-brainwiki]` table from `~/.codex/config.toml` for Codex.
3. Delete the state directory named in your config (`state`, default `.state-secure` beside `ox_retrieval.py`). Everything the connector writes lives there: `env()` in `ox_retrieval.py` points TEMP, TMP, USERPROFILE, APPDATA, LOCALAPPDATA, BASIC_MEMORY_CONFIG_DIR, BASIC_MEMORY_HOME, HF_HOME and FASTEMBED_CACHE_PATH into the state directory, and `index()` writes only `staging/`, `bm/config.json` and `receipt.json` under it. These connector writes are separate from Obsidian's vault settings/global app data and the agent's authorized onboarding outputs.
4. Optionally delete the repository clone, including its `.venv/`. Your source notes are never modified by the connector, so there is nothing to roll back in them.

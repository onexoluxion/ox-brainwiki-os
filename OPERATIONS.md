# Operations

Run index manually after source edits; no competing watcher or scheduler. It filters before copying, removes deleted staged Markdown, then calls `basic-memory project index main`. Basic Memory writes only staging and its isolated .state-secure/bm database. Model downloads and cache are under .state-secure; initial installation/download needs network. Inference is local FastEmbed bge-small-en-v1.5. Full dependency footprint is 161 installed packages, pinned transitively in uv.lock. Do not interpret this as a small extracted engine.

Operations serialize through an exclusive Windows state-file lock. Concurrent processes receive a sharing failure rather than reading a rebuilding index. The state directory must have a restricted DACL allowing only the current user, SYSTEM and Administrators; newly created state is restricted at creation. Existing broadly accessible state is rejected, never silently chmodded or adopted. Choose a new state path for migration. The selected state parent must exist. Ancestors are pinned against rename while the lock is held; preexisting linked state is rejected. Same-user malicious processes and administrators are outside the local account isolation boundary.

Rebuilds clear the receipt before changing staging and publish it only after successful backend indexing, stable source hashes and a vector probe. Failure leaves semantic retrieval unavailable until a successful rebuild. This avoids maintaining multiple full index copies. Do not change production source ACLs as part of setup; the reader protects against traversal and source-directory substitution using handle checks/pins.

A missing receipt, source change or failed index prevents semantic retrieval. Exact search and reads remain live. A subprocess failure gives a generic maintenance error; backend diagnostics remain in the isolated Basic Memory logs. A model failure never falls back to lexical search under semantic mode. Status does not actively probe the model. Index success includes a vector probe and fingerprints of source inventory, database, configuration, dependency versions and model artifacts; this is not general query-quality certification.

## Configuration

The `state` path's parent directory must exist before `index`, `status` or `serve` runs: retrieval pins that parent while the lock is held and creates only the state directory itself (with `.state` beside the config, the parent is the clone root). On Windows, the model cache lives under the state directory, and Windows refuses paths longer than 259 characters while long paths are disabled; the connector therefore refuses a state path longer than 136 characters (259 minus the model cache suffix) unless `LongPathsEnabled` is set, with the message `state path too long for Windows: <N> characters, limit 136; use a shorter install or state path, or enable Windows long paths (LongPathsEnabled)`. Recommended install path: a short top-level folder (the timing in README.md was measured with a 46-character state path).

`acceptance.py` is a developer check: it indexes and queries the repository's own `fixtures/notes` into the default state directory (`.state-secure`) and is not part of onboarding; the onboarding health check is `status --config retrieval.config.json` reporting `"fresh": true` plus one exact `search` through the connector.

Recovery: stop the connector, preserve the failed state privately and select a new unused state path in the config, rerun index, then run `status` and one exact `search` through the connector. Source notes are never changed by indexing; rollback means stop using this connector. Do not remove source data. State contains staged content and vectors and needs the same permissions as the source; do not publish it. The state directory must remain private to the configured Windows user.

Initial candidate evidence, recorded 2026-11-06: boundary review, remote scan, clean locked installation, private-corpus acceptance and actual Codex client checks were reported for the versions named in RELEASE_CHECKLIST.md. In the pilot, Claude model-mediated acceptance was blocked by that environment's API authentication (401); on 2026-11-06 Claude Code registration, `status` and one exact `search` through the connector were verified. These dated receipts do not certify later revisions, the current user's installation or newly added acceptance cases. Full replacement of an existing retrieval setup requires checks in its intended clients and routine-work quality/latency evidence. Immutable model-download pinning and model redistribution remain open; see MODEL_PROVENANCE.json and THIRD_PARTY_NOTICES.md.

Release gates: cabinet templates and synthetic routing acceptance, reviewed portable Calibrate rights/security and mode tests, primary-source attribution for the Karpathy foundation, package/license/private-data audit, claimed-platform tests. These were deliberately not substituted with copied private skills.

## Evidence and acceptance

Keep a dated receipt for the exact version and destination being checked. Record the command or tool, exit code or error, inputs covered, observed result and remaining gaps. A process running or a connector reporting Connected establishes availability only. Read the complete result before claiming success: a failed batch can leave valid partial work, and a successful local change can still be absent from another client or destination.

| Claim | Evidence required |
|---|---|
| Sources are current | Source inventory matches the receipt; source dates cover the question. A file's checkout time is not its evidence date. |
| Retrieval works for a task | An exact identifier and a paraphrased question return the expected allowed source; read back the original and check its scope/date. A fresh index alone is not query-quality evidence. |
| A repair is installed | The installed version or hash matches the reviewed change, followed by a successful operation through the intended client. An isolated test is evidence for that test environment only. |
| Recovery works | Restore source/configuration backups into a separate private location with unused state, rebuild, then check source hashes, expected retrieval, exclusions and read-only behavior. State explicitly what was not restored. |
| A recurring process is reliable | Dated receipts from actual unattended runs and an observed failure-notification path, if a scheduler is separately configured. Manual runs do not count as unattended runs. This package adds no scheduler. |
| Retrieval improved | Comparable before/after corpus versions, held-out questions, configuration and scoring. If a baseline is unavailable, record a new baseline without claiming improvement. |

Before maintenance, inspect the last receipt and any active owner; avoid competing rebuilds. Preserve failed state and logs privately. Reconcile source and destination receipts before retrying or marking work complete. Keep recovery copies until separately authorized cleanup; never delete a lock or weaken access checks to force progress. The recovery and acceptance steps above are procedures, not claims that these checks have run on a user's installation.

## Uninstall and rollback

1. Remove the connector registration: `claude mcp remove ox-brainwiki` in Claude Code (usage read from `claude mcp remove --help`), or delete the `[mcp_servers.ox-brainwiki]` table from `~/.codex/config.toml` for Codex.
2. Delete the state directory named in your config (`state`, default `.state-secure` beside `ox_retrieval.py`). Everything the connector writes lives there: `env()` in `ox_retrieval.py` points TEMP, TMP, USERPROFILE, APPDATA, LOCALAPPDATA, BASIC_MEMORY_CONFIG_DIR, BASIC_MEMORY_HOME, HF_HOME and FASTEMBED_CACHE_PATH into the state directory, and `index()` writes only `staging/`, `bm/config.json` and `receipt.json` under it. Nothing else is written outside it.
3. Optionally delete the repository clone, including its `.venv/`. Your source notes are never modified by the connector, so there is nothing to roll back in them.

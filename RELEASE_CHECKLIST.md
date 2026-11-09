# Release checklist

> Historical v0.1 candidate evidence follows. It does not certify a later commit or the current user's installation; use the operator steps below for a new candidate.

For the 0.2.0 runtime update, see [its design, boundaries and validation](RUNTIME_DESIGN.md#validation-for-020). The original receipts below remain unchanged.

Each proof lists the command run, its exit code and the evidence. Proofs ran on 2026-11-06 against commit `ad06a2d360c91c9a8054c0c7413137d82efb9e16`; the only changes after it are this file and one README sentence (registration note). Host: Windows 11, uv 0.12.10, Python 3.12.14, Git 2.55, `LongPathsEnabled = 0`.

## Release commit

- Code commit the proofs ran on: `ad06a2d3` (guard, onboarding fixes).
- Release commit: the commit that adds this file (docs only).
- Repository: private until the publish steps below are run.

## Proof 1 clean install

- Fresh clone into an empty short-path folder (`...\Temp\oxos\proof1\repo`, state path 64 characters), `git checkout ad06a2d3`: exit 0.
- `uv sync --frozen --python 3.12` in that clone: exit 0.
- Executing the clone's Python there was refused by the build session's permission classifier (not a product failure), so the remaining steps ran on the build checkout at the same commit, state path 48 characters:
  - `.venv/Scripts/python.exe ox_retrieval.py index`: exit 0, 7 s with the model already cached. First download earlier the same day: 27 s, state directory 67 MB, model files 65 MB under `.state-secure/models/`.
  - `.venv/Scripts/python.exe ox_retrieval.py status`: exit 0, `"fresh": true`, `"model_available": true`, backend `basic-memory 1.0.0`.
  - Over MCP stdio (`serve`, minimal JSON-RPC client): `tools/list` = search, read, list, status.
  - `search` exact `WO-2048`: `notes/shipment.md`, 0.12 s.
  - `search` semantic "Why was the mug delivery pushed back?": `notes/shipment.md` first, 4.73 s.
  - `read notes/shipment.md`: content returned with sha256 and `untrusted_content: true`.
  - `read notes/private/hidden.md`: `path denied`. `search` with scope `notes/private`: `path denied`. Exact search for the excluded note's own text in the default scope: 0 results. `list notes` omits `private`.
  - Fixture sha256 before and after index, tool calls and tests: identical.
  - `python -m unittest test_pathlen test_retrieval test_protocol test_deployment`: exit 0, 25 tests, OK (skipped=1, symlink privilege).
- Earlier the same day, a clone under a 138-character state path reproduced the Windows MAX_PATH failure (model file path 261 characters, errno 2, index exit 1 after 52 s). The guard added in `ad06a2d3` now refuses such a path before touching disk: live check on a 143-character path exited 1 with `state path too long for Windows: 143 characters, limit 136`.
- Not verified: a fresh clone executing on a machine the author has never used. Script for the operator: see Publish steps.

## Proof 2 onboarding

- Fresh subagent, scripted answers for a fictional business (Northline Calibration Lab, industrial calibration services, no marketplace), skill text plus `skills/onboard/example-answers.md` only, clone at `...\Temp\oxos\proof2\repo`, commit `ad06a2d3`: all six steps done, logged in `identity/onboard-log.md`.
- Resulting folder: filled `identity/business.md`, `goals.md`, `agent-voice.md`, `sources.md`, `retrieval.config.json` (root = the business folder, state `.state`, allow `notes`), the business folder with `contract-renewals-2027/PROJECT_INDEX.md`, `task-and-source-guide.md`, two seed notes and one approved capture.
- Its own queries: exact `CAL-7731` returned `notes/contracts/renewal-register.md` (only result); semantic question returned only the user's files; `read` matched the file on disk; `status` `"fresh": true`; exact search for a word from the capture returned the capture.
- Re-run of step 3 alone with the same answers: every other step's file byte-identical (sha256 compare); only the log gained a line.
- Grep of the business folder for the private-content terms: zero hits.
- Polish items the reviewer flagged, not fixed in v1: step 3 asks one question for two placeholders in two places; step 3 re-run has no pristine template copy (the identity files are the templates); the registration-fallback sentence precedes "through the connector" without saying how an agent without a client proceeds (it drove `serve` directly); "open the file" is undefined for a terminal agent; the log format has a fourth form for a declined capture; a first user with an empty notes folder gets empty query results until they add notes.

## Proof 3 private-content sweep

- Committed tree at `ad06a2d3` (39 files, clean) and the proof-2 output folder: zero hits for machine paths, user name, business and counterparty names, account id, session UUIDs and state directory names. Only name-adjacent strings: the `One Xoluxion` credit (LICENSE, README, three skills) and third-party GitHub URLs (Basic Memory, MCPVault).
- No committed `.db`, `.onnx`, `.state`, `.lock` other than `uv.lock`, or file over 1 MB (largest: `uv.lock`, 263 KB). `uv.lock` URLs: `files.pythonhosted.org` and `pypi.org` only.
- Instruments validated with positive controls before trusting the zero.

## Proof 4 licensing and secrets

- `LICENSE`: Apache License 2.0, canonical text (sha256 `cfc7749b96f63bd31c3c42b5c471bf756814053e847c10f3eb003417bc523d30`), appendix `Copyright 2026 One Xoluxion`.
- `THIRD_PARTY_NOTICES.md`: generated by `tools/gen_notices.py` from installed package metadata, 161 distributions; regenerated on `ad06a2d3`, byte-identical. Two licenses unresolved from metadata: `py_rust_stemmers 0.1.8` (UNKNOWN) and `mmh3 5.3.1` ("see package"). Basic Memory AGPL-3.0-or-later statement (separate CLI process, not vendored), embedding model statement (no weights shipped; upstream BAAI model card reads MIT, read 2026-11-06), MCPVault inspiration credit.
- `rafter secrets .`: no secrets detected, on `9c86f8eb` and on `ad06a2d3`.
- `rafter run --mode fast` on `9c86f8eb`: 3 findings, all severity note (R-E617E, starting a process with a partial executable path, in `test_deployment.py` and `test_retrieval.py`, the same accepted test-only notes as the private pilot). Not rescanned after `ad06a2d3` (a 20-line guard, one test file and documentation) under the one-scan-per-branch quota rule. Scan id not captured.

## Verified beyond the four proofs

- Claude Code registration with the README command (`claude mcp add ox-brainwiki -- <repo>/.venv/Scripts/python.exe <repo>/ox_retrieval.py serve`): reported Connected. Headless `claude -p` through that connector: `status` (fresh true) and exact `search` `WO-2048` returned `notes/shipment.md`; final result success in 7 turns. Registration removed afterwards with `claude mcp remove ox-brainwiki --scope local`: list shows none.
- Codex end-to-end: verified in the private pilot of the same connector code (status, list, exact, semantic, read), not repeated here.

## Not verified in v1

- Fresh-clone execution on another machine (classifier-blocked here; operator script provided).
- Codex `config.toml` snippet as written in README.md (shape matched to a local config only).
- Non-Windows platforms: not supported in v1.
- Embedding model download pinning by code: not built in v1; tested hashes in `MODEL_PROVENANCE.json`.
- The two unresolved dependency license strings above.

## Publish steps (operator)

The receipts above describe the initial candidate, not later changes or a new release. Recheck affected proofs for the exact candidate commit and retain dated results. This package does not depend on scripts from another workspace.

1. Record the reviewed candidate's full commit hash, clone into a new short-path directory and check out that exact commit. Follow [Install](README.md#install), then check the fixture queries, read-only behavior and exclusions from Proof 1. Record unavailable checks explicitly; do not relabel an existing-install run as a fresh-clone run.
2. Exercise the relevant [cabinet acceptance cases](cabinet/acceptance-cases.md), review this checklist and README, and run the local secrets/private-content checks on the complete proposed tree. Check metadata, commit messages and review text as well as files; keep identities, account data, private paths, evidence and links out of the distributable. Verify the scan can detect a disposable positive control outside the release tree before relying on a zero result.
3. Have the repository owner review the exact commit, remaining limitations, licensing and intended audience. Only after explicit publication approval, confirm that commit is on the intended release branch and use the owner's repository hosting workflow to set visibility and create a tag/release. Read back visibility and the tag's commit before reporting publication. Preparing a branch or passing these checks does not grant publication permission.

# Release checklist

Each proof lists the command run, its exit code and the evidence path. A proof with a pending line is not passed.

## Release commit

- Commit SHA: pending
- Repository: pending

## Proof 1 clean install

- Fresh clone into an empty folder: pending
- `uv sync --frozen --python 3.12`: pending
- `ox_retrieval.py index` against fixtures (exit code, model download size and time): pending
- `search` exact `WO-2048`: pending
- `search` semantic paraphrase: pending
- `read` of a fixture note: pending
- Excluded note (`fixtures/notes/private`) refused: pending
- Fixture hashes unchanged after the run: pending

## Proof 2 onboarding

- Fresh subagent with scripted answers for a fictional business completes the six steps from `skills/onboard/SKILL.md` alone: pending
- Resulting folder has filled identity, cabinet and config: pending
- Its own queries return its own files: pending
- Re-running one step leaves the other steps' files unchanged (hash compare): pending

## Proof 3 private-content sweep

- Grep of the repository and the proof-2 output folder for the private-content term list in the build prompt (machine paths, user names, business and counterparty names, account ids, session UUIDs, state directory names): pending
- Each remaining hit justified here: pending

## Proof 4 licensing and secrets

- `LICENSE` (Apache-2.0) present: pending
- `THIRD_PARTY_NOTICES.md` regenerated with `tools/gen_notices.py` on the release commit: pending
- `rafter secrets .` clean: pending
- One `rafter run --mode fast` on the final commit only: pending

## Not verified in v1

- Claude Code end-to-end inference through the connector (pilot returned API 401): pending
- Non-Windows platforms: not supported in v1
- Embedding model download pinning by code: not built in v1, see `MODEL_PROVENANCE.json`
- `claude mcp add` and Codex registration commands as written in README.md: pending

## Publish steps (Freddy)

- Review this checklist and the four proofs: pending
- Make the repository public: pending
- Tag the release: pending

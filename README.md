# OX Retrieval — private Windows pilot



Start with a private source folder, identify authoritative sources with a project entry map, and preserve the existing capture/propose/approve workflow. Synthetic acceptance and a separate 94-file private pilot have passed; private data is never committed. Cabinet and Calibrate documentation passed synthetic acceptance; installable assets remain pending rights review; no private skills are bundled.



Python 3.12, Basic Memory 1.0.0, FastMCP 4.1.3. Install in this directory:



```powershell

uv sync --frozen --python 3.12

.venv/Scripts/python.exe ox_retrieval.py index

.venv/Scripts/python.exe ox_retrieval.py status

.venv/Scripts/python.exe ox_retrieval.py serve

```



MCP stdio exposes search, read, list and status. The default corpus is fixtures/notes; fixtures/notes/private is excluded. Each semantic request starts one Basic Memory CLI child and explicitly passes --mode semantic. There is no persistent second server or watcher. The supported CLI boundary avoids unstable Python internals. This has cold-start overhead; throughput is not qualified.



`search("WO-2048", mode="exact")` uses case-insensitive literal matching with punctuation preserved. Basic Memory FTS successfully finds this identifier; literal matching provides distinct substring semantics rather than claiming FTS is literal. `search("Why was the delivery of cups postponed?")` uses the backend vector engine. Results cite original relative paths and current excerpts, not trusted instructions. No cross-mode score comparison. Read returns original content, hash and source mtime. List is recursive Markdown listing. Status compares hashes with the indexing receipt; it does not claim the model is healthy until a vector query succeeds.



See DESIGN.md, OPERATIONS.md and ACCEPTANCE.md. A private opt-in pilot is deployed; public release and full production replacement remain gated. See [deployment](DEPLOYMENT.md).



Basic Memory by Basic Machines supplies indexing and retrieval (AGPL-3.0-or-later). MCPVault by Mauricio Wolff / bitbonsai informed the architectural comparison; no MCPVault source is copied. Neither project endorses this candidate.



Hardening now enforces restricted Windows state ACLs, exclusive operation locking, directory pins, final-handle source checks, model/config/index identity and a completed vector probe. Independent boundary review, remote security scan and private Codex acceptance passed. Claude connector health passed; its model authentication blocked end-to-end acceptance.



## Explicit configuration (Windows only)

Use `python ox_retrieval.py index --config candidate.json` (also `status` or `serve`).

The JSON object must contain exactly `root`, `state`, `allow`, and `exclude`:

`{"root":"fixtures","state":".state-secure","allow":["notes"],"exclude":["notes/private"]}`.

Root/state resolve relative to the configuration file. Unknown/duplicate fields and malformed scopes fail validation. Without `--config`, synthetic fixture defaults remain. This implementation requires Windows and Python 3.12; it is not portable to POSIX.



Community navigation and calibration documentation: [community guide](community/README.md). The synthetic routes passed fresh-session review; installable skill packaging remains separate.

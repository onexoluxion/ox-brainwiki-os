# Runtime release design

Scope: scoped semantic search, durable indexing receipts, completeness checks and bounded error diagnostics. The four read-only MCP tools remain the external interface. Indexing is manual and writes only operator-owned isolated state. No dependency code, private notes or operational artifacts are imported.

## Decisions before implementation

- Search scope is validated before launching the backend and passed as its supported folder argument. Returned paths are still checked against the allow/exclude rules and read from original files. Query text is a separate subprocess argument after `--`; no shell is used.
- Receipts use a versioned closed JSON shape, a 2 MiB byte limit, duplicate-key rejection and bounded field validation. Missing, legacy, malformed or oversized receipts are unavailable evidence, never fresh. Publication uses a private same-directory temporary file, flush/fsync and atomic replacement under the existing exclusive state guard. This gives atomic reader visibility, not a guarantee that the directory entry survives power loss; a lost receipt requires rebuilding. A failed rebuild invalidates its receipt before changing staged content.
- Completeness compares the exact allowed source inventory with the pinned backend's indexed file/sync checksums, ready vector chunks, expected embedding identity and stored vector membership. The sync checksum accounts for backend normalization of staged frontmatter without changing the original source. Read only the isolated configured database with fixed parameterized queries and bounded work. An unknown schema, unsupported vector store, missing project or unavailable database is `unknown`, never a pass. Status returns counts/reason enums, not indexed content or private paths.
- Backend diagnostics expose a fixed code, operation and optional numeric exit code. They never include subprocess output, queries, source content, absolute paths or arbitrary exception text. The last failure is process-local; success clears it. Timeout, output overflow, malformed backend output and nonzero exit remain distinct. No persistent diagnostic log or new network endpoint is added.
- Existing source/state containment, directory pins, ACL validation, hard-link checks, exclusive locking, child job containment and output/time/corpus limits remain required. No cross-request freshness cache is introduced; source changes during search still invalidate the response.

## Threat model

Data flow: agent request -> validated tool arguments -> contained local backend; allowed Markdown -> isolated staging/index -> bounded result paths -> checked original reads. Receipt and completeness checks use only isolated state while the exclusive guard is held. Initial dependency/model installation retains its existing network behavior; this release adds no fetcher or telemetry.

| Boundary / abuse case | Control |
|---|---|
| Search arguments try to escape scope or become flags | Validated scope, argument arrays, `--` before query, result path revalidation |
| Corrupt state masquerades as a successful index | Bounded strict receipt parsing plus current source, artifact and per-document completeness checks; unknown fails closed |
| Crash while publishing success | Invalidate first, publish atomically only after indexing and checks; interrupted state requires another manual rebuild |
| Database or receipt input consumes excessive work | Fixed schema adapter, read-only SQLite, row and byte limits, query deadline/progress guard; existing corpus limits remain |
| Child fails, hangs or prints sensitive data | Existing job/timeout/output limits; only allowlisted diagnostic metadata reaches the client |
| State is redirected to another location | Existing private ACLs, no source/state overlap, link rejection, directory pins and exclusive guard remain active |
| Source changes between validation and response | Recheck freshness before publishing results; preserve original read validation |

Local notes, derived vectors and receipts remain sensitive user data under existing state ACLs. Tests use invented documents and disposable private state, never real user corpora. No credentials are required by new code. Same-token malicious processes and administrators remain outside the existing isolation guarantee. Hash/receipt validation is not proof of semantic relevance, model-download authenticity or backup recovery.

Backend checksum/sync fields describe that backend's ingestion contract, not independently authenticated facts. Database changes after a completed receipt invalidate its artifact fingerprint, including a forged sync field. An operator who can rewrite the database and receipt together can forge evidence; unsigned receipts do not defend against that trusted-account attack. Artifact hashing is bounded to 1,000 model-tree entries, 100 model files, 256 MiB per artifact and 512 MiB in aggregate. State beyond those limits is unavailable evidence, not a partial success. The existing state guard still assumes an operator-owned state tree.

## Acceptance and release gates

Synthetic regressions cover more than 50 distractor documents with one scoped target; interrupted/invalid/oversized receipts; missing/stale/excluded/incomplete index rows; wrong model identity; backend timeout/nonzero/output overflow; exact and semantic MCP calls; unchanged source hashes; and existing Windows path/ACL/link/lock checks. Unknown completeness must not be reported as ready. Old receipts require a manual rebuild.

Run local secrets and private-content checks, independent Rafter code review and the full test suite before pushing the final candidate. Re-read shared Fast quota immediately before the single remote scan; use repository CI instead if it owns that scan. Review findings before merge. A scan that cannot run is not a passing gate. Keep release evidence generic and identify unverified platforms/client checks explicitly.

## Validation for 0.2.0

Verified on Windows with Python 3.12 and the locked dependency environment. These are synthetic local checks, not another-machine acceptance or a retrieval-quality benchmark.

| Check | Result |
|---|---|
| `uv sync --frozen --offline` | Exit 0; 161 installed packages checked; no dependency version upgrades |
| `python -m unittest test_pathlen test_retrieval test_deployment test_runtime` | Exit 0; 44 tests run, one skipped because symlink privilege was unavailable |
| `python test_protocol.py` | Exit 0; four-tool stdio discovery and exact search |
| `python runtime_acceptance.py` | Exit 0; real backend and MCP exact/semantic/read/status, 60 distractors, exclusions, corrupt receipt, missing vector and unchanged source hashes |
| Create the ignored `.state` test parent, then `python acceptance.py` | Exit 0; existing modification/rename/deletion and stale-index acceptance |
| Local patterns secrets scan | Exit 0; zero findings; a synthetic positive control outside the release tree was detected |
| Candidate private-content pattern check | Zero matches across all tracked and non-ignored candidate files |
| Independent Rafter code review | No remaining release-blocking issue after fixes and re-review |

Remote security analysis is a separate required pre-merge gate on the pushed candidate; its final result belongs in the associated pull request/release. No remote scan result is asserted by this local-validation table. Full client enrollment, another machine, non-Windows support, model-download authenticity and general performance gains are not established here.

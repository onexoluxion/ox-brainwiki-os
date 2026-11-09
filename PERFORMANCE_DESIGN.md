# Runtime 0.3.0 performance design

Measure released 0.2.0 before changing runtime code. Use only invented bounded corpora and the existing public model cache. The benchmark driver is shared across the frozen baseline and candidate; dependencies and model artifacts remain identical. Numerical acceptance targets are frozen after the baseline and before implementation.

## Design and security decisions

Data flow: synthetic corpus -> existing contained reader/indexer -> isolated private SQLite/model state -> bounded benchmark summaries. Summaries contain operation labels, counts, timings and allocation/resource measurements; never absolute paths, host/user identifiers, query text, note contents, logs or credentials. Baseline source is exported from its public tag, not from another workspace.

- Exact matching may share one streaming source read with inventory hashing. Keep scope checks, actual-opened-file validation, directory pins, global corpus limits, result order/limits and the final full freshness check. Do not retain corpus bodies after the operation or introduce cross-request caches.
- Completeness may drain fixed read-only cursors in bounded batches. Preserve every report field, accepted checksum semantics, row/field/work limits and fail-closed unknown. Do not keep simultaneous full chunk/vector row lists plus derived collections. Any malformed/unavailable/over-limit input must not become a partial success.
- Index staging may skip a write only after a bounded byte-hash comparison proves an existing regular destination identical to the checked source. Keep existing link/ACL/hard-link validation and exclusive locking. Backend-normalized frontmatter is not a reason to trust different bytes. Deletions, backend indexing, vector probe, receipt invalidation/publication and final source checks remain.
- Benchmark paths are explicitly selected by the developer; preparation refuses existing workspaces, and output creation refuses replacement. Reuse model cache only under both source/destination state guards with link-preserving copy. No private configuration discovery, new network endpoint, watcher, worker, telemetry or dependency upgrade is introduced.

## Threat review

| Abuse / failure | Required behavior |
|---|---|
| Source changes during exact search or indexing | Original read checks and full post-validation remain; semantic search still has both pre/post freshness checks |
| Cached metadata hides equal-size/mtime changes | No metadata-only freshness cache; byte hashing remains authoritative |
| State or cached models are redirected | Existing private ACLs, link rejection, directory pins, hard-link checks and exclusive locks remain |
| Cursor stops early or exceeds limits/deadline | Unknown result with original bounded report shape, never success based on partial rows |
| Different staged bytes appear unchanged | Compare actual bounded bytes; rewrite when unequal; do not substitute a backend sync checksum |
| Benchmark leaks data or overwrites records | Invented fixtures, new-workspace/output requirements, summaries without content/paths, no private source access |

Same-token hostile processes and administrators remain outside the existing isolation guarantee. Performance results are local observations, not universal throughput, semantic quality or another-machine claims. Persistent workers and filesystem watchers are deferred. Review changed path/SQLite handling and complete the existing Rafter gate before release.

The benchmark executes explicitly selected trusted implementation code; it is not a sandbox for third-party projects. Resource hooks use plain functions without mock call-history retention. Latency trials exclude tracing/sampling; resource comparisons use the same final hook implementation for both versions.

## Baseline protocol

Use 10, 100 and 1,000 short Markdown documents (the exact deterministic byte generator and repetition count are retained), plus one excluded document. Measure list, exact search, status, scoped semantic search, unchanged reindex and an edit/restore pair. Time repeated calls separately from an instrumented pass; distinguish a new wrapper process from repeated requests with a prepopulated model cache. Record p50/p95, wrapper reads/writes, backend time/count, completeness time/count, sampled process-tree working set and Python allocation peak. A standalone completeness pass measures that module independently of embedding inference. Questions and benchmark code remain outside indexed corpora.

The initial approximately 4 KiB/document preparation pilot timed out first-indexing 1,000 documents under the unchanged 300-second backend limit. Preserve that failure as an unscored capacity observation; do not report zero latency, claim successful preparation or increase the timeout. The short-note comparison is a separate workload and makes no performance/capacity claim for that failed case.

Retain baseline/candidate source versions, model/dependency identities and raw numeric samples. Check output equivalence with volatile timestamps removed; preserve source byte hashes. Report small sample counts and sampled-RSS limitations explicitly. No measured improvement is asserted before the comparison.

Read operations deliberately reuse the same healthy prepared index across implementations. Source bytes, models and dependencies are verified, and initial index fingerprints are recorded; code imports are checked against the selected implementation root. Mutating cases perform the same unmeasured staging warm-up and restore source bytes, leaving a healthy logically equivalent index, although row IDs/timestamps can change. Final read-only confirmation runs compare baseline/candidate against an identical database fingerprint without intervening reindexing. The edit/restore case is explicitly a pair of full indexes; it is not reported as single-edit latency. Preparation time is outside steady-state timing and any setup failure is retained separately.

## Frozen acceptance targets (before runtime edits)

The released baseline read trials measured exact-search medians of 471.388 ms at 100 documents and 5821.460 ms at 1,000 documents (three timing trials). Standalone completeness medians were 20.569 ms and 127.850 ms. Finish collecting the frozen implementation's index trials and repeat resource profiles with the final shared driver; these observations set targets, not a speed claim.

- Exact search: at least 30% fewer checked source reads and at least 15% lower median latency at both 100 and 1,000 documents in the final matched confirmation.
- Completeness: at least 25% lower Python allocation peak at 1,000 documents, with identical reports; no material latency regression.
- Staging: zero writes for byte-identical staged notes after warm-up. Real byte differences, even with preserved size/mtime, still require replacement. Keep backend index and vector-probe calls.
- All result signatures and source hashes must match. Investigate control-operation p95 or sampled RSS regressions greater than 10%; repeat noisy observations rather than silently discard them. Small-sample p95 is an observed maximum, not a population estimate.

Win32 setup may also be shared as immutable module bindings: create the DLL with `use_last_error=True`, assign prototypes once, and keep all handles, attribute structures and path buffers invocation-local. This reuses API setup, never filesystem state. Existing handle-derived path validation and reverse-order cleanup remain unchanged. Concurrent reads and failure cleanup require regression coverage. The release remains Windows-only; no new portability claim is made.

## Local security review

Independent Rafter CWE Top 25 and LLM review found no actionable defect in the candidate. The changed boundaries were traced explicitly:

| Boundary | Evidence |
|---|---|
| Filesystem reads and exact matches | `ox_retrieval.py`: checked source reader, `_scan_sources`, complete scan before return, final `status`; content remains untrusted |
| Staging writes | `_write_if_different` compares bounded bytes, rejects linked destinations; `index` retains guarded state, invalidation, backend/probe and post-checks |
| Shared native bindings | `_WindowsAPI` sets signatures once with thread-local last-error handling; `pinned_directories` and `_read_pinned` keep handles/buffers local |
| SQLite consumption | `index_health.py`: fixed parameterized queries, read-only connection, bounded fields/rows/batches/deadline; all partial failures return the untouched unknown report |
| Benchmark execution and privacy | `verify_workspace` admits exact invented fixtures/configs, `prepare` guards cache copies, subprocess uses argv, output uses exclusive creation and counts/hashes only |

Local pattern-engine secrets scan returned no findings (exit 0). An external invented credential positive control was detected (exit 1), proving the detector was active. Private-content pattern review found no matches in distributable source. These free checks are separate from the required remote Fast scan on the final pushed candidate.

## Drift control

Sequential repeats showed substantial wall-clock drift, including slower listing results despite identical candidate listing code. Keep these samples; do not select the fastest run. `paired_benchmark.py` adds seven alternating baseline/candidate pairs at each size, reversing execution order on alternate pairs. Each trusted implementation runs in a fresh, fixed-lifetime benchmark process after identical synthetic-fixture and healthy-state checks. It measures the same five read operations without resource instrumentation. Database bytes must remain identical before/after each worker and across both implementations; dependencies, model/source identities and result signatures must also match before a report is written.

This confirmation controls execution order rather than claiming an idle or dedicated machine. It is distinct from a long-lived MCP throughput test. Allocation and source-read comparisons still use the shared final resource hooks; alternating trials confirm latency separately. No production worker is introduced.

Run the real-backend acceptance scripts sequentially: they share this checkout's guarded model-cache source, and the exclusive lock intentionally rejects overlapping use.

## Validation for 0.3.0

| Check | Observed result |
|---|---|
| `python -m unittest discover -v` | Exit 0; 61 tests run, one existing skip because Windows symlink privilege was unavailable; stdio discovery/exact check also passed |
| `python runtime_acceptance.py` | Exit 0; real backend and MCP exact/semantic/read/status, one scoped target with 60 distractors, exclusions, corrupt receipt, missing vector and unchanged source hashes |
| `python acceptance.py` | Exit 0; legacy original-content/exclusion checks plus modification, rename, deletion and stale-index rejection |
| `uv lock --offline --check` | Exit 0; dependency versions unchanged; only this project's version becomes 0.3.0 |
| Synthetic benchmark assertions | Exit 0; identity/signature/source checks, frozen exact/allocation/write targets and both alternating confirmations |
| Local security/privacy | Exit 0; zero pattern-engine secret findings, no private-content pattern matches; independent CWE/LLM and benchmark review found no actionable defect |

The first parallel acceptance launch was rejected by the shared-cache exclusive lock. The sequential rerun passed; locking was not weakened. Failed logs remain outside the distribution. Remote Fast scan findings and the exact reviewed candidate are recorded in the release PR before merge. See [observed results and limitations](PERFORMANCE_RESULTS.md); the measurements do not qualify general semantic/startup/reindex throughput or larger-note capacity.

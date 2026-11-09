# Runtime 0.3.0 measurements

Compared with released 0.2.0 using invented short Markdown documents, the same locked Windows/Python 3.12 environment and identical public model artifacts. These are local observations on a shared host, not general throughput or semantic-quality guarantees. Source contents, queries, absolute paths, machine identifiers and raw logs are excluded from the report.

## Read confirmation

Seven alternating pairs per size, with execution order reversed on alternate pairs. Each implementation runs in a fresh benchmark process after fixture, health and inventory checks. The timed direct call excludes interpreter startup; `new_process_status` separately includes a new CLI process. Database bytes, dependency/model/source identities and output signatures match across all pairs. This condition is distinct from repeated requests in a long-lived MCP server.

| Documents | Exact median 0.2.0 | Exact median 0.3.0 | Reduction | Checked source reads, 0.2.0 -> 0.3.0 |
|---:|---:|---:|---:|---:|
| 10 | 99.753 ms | 85.536 ms | 14.3% | 30 -> 20 |
| 100 | 483.143 ms | 341.870 ms | 29.2% | 300 -> 200 |
| 1,000 | 5,833.320 ms | 3,911.588 ms | 32.9% | 3,000 -> 2,000 |

Exact search improves in all seven pairs at both 100 and 1,000 documents. Median per-pair reductions are 27.8% and 32.4%; gains occur with either execution order. The workload has one literal target and the default result limit. Other query distributions can save fewer reads.

A separate shared-hook allocation profile on the identical database measured the 1,000-document completeness pass at **996.60 KiB -> 675.03 KiB peak Python allocation (32.3% lower)**. This is not total process memory. Tracing and RSS sampling are excluded from latency trials. RSS is a sampled sum of parent/descendant working sets, not unique physical memory; in-process read/write counters exclude child file I/O.

## Indexing observations

After the same unmeasured staging warm-up, unchanged indexing wrote **zero staged notes** at all three sizes, versus 10/100/1,000 writes in 0.2.0. Each index still called the backend index and vector probe. An edit/restore pair wrote two staged notes, versus 20/200/2,000, with four backend calls retained. Sources were restored byte-for-byte and the final index remained healthy. Actual differing bytes are rewritten; this does not trust mtime or backend sync metadata.

| Documents | Unchanged index median, 0.2.0 -> 0.3.0 | Edit/restore pair median, 0.2.0 -> 0.3.0 |
|---:|---:|---:|
| 10 | 8.033 -> 9.571 s | 17.180 -> 21.262 s |
| 100 | 9.362 -> 10.994 s | 28.075 -> 24.185 s |
| 1,000 | 21.137 -> 21.801 s | 47.730 -> 37.932 s |

These are two sequential timing samples per case, outside profiling. An edit/restore pair contains two complete indexes. Backend startup and validation remain significant costs. Small-index trials were slower in the later run; the measurements do not establish a general reindex latency improvement. The deterministic write reduction is the qualified indexing benefit.

Three alternating semantic pairs confirmed mixed small differences: medians were 5,456 -> 5,377 ms at 10 documents, 5,789 -> 6,135 ms at 100, and 8,441 -> 8,325 ms at 1,000. These are direct semantic calls in fresh benchmark workers after health/inventory checks, with a prepopulated model cache. No semantic latency improvement is qualified from this small sample. The four public tools and both semantic freshness checks are unchanged.

## Controls and limits

- Sequential samples drifted substantially even for identical listing code. All sequential samples are retained alongside the alternating confirmation. The first candidate's larger cursor batches missed the frozen allocation target; the final implementation uses 64-row batches and releases each drained batch before fetching another.
- Tail latency is not uniformly better. In alternating trials, new-process status at 100 documents had a 4.3% higher median and a 12.1% higher observed maximum; completeness at 1,000 documents had a 9.2% lower median but a 20.5% higher maximum. Exact search at 10 documents also had a higher maximum despite its lower median. No universal tail/startup improvement is claimed. With seven samples, the reported p95 is the observed maximum, not a population estimate.
- The initial approximately 4 KiB/document first-index pilot timed out at 1,000 documents under the existing 300-second backend limit. This failed preparation is retained as an unscored capacity observation. The successful comparison uses a separate short-note corpus and does not resolve that failed capacity case.
- Completeness measures index coverage, not relevance. Semantic requests still start a backend subprocess and retain both freshness checks. No model/dependency upgrade, persistent runtime cache, worker or watcher was introduced.

The design, frozen targets and review boundaries are in [PERFORMANCE_DESIGN.md](PERFORMANCE_DESIGN.md). [Sanitized numeric observations and provenance](performance_results.json) retain raw samples, successful and failed conditions, intermediate measurements and the comparison fingerprints. Initial full-baseline resource time/allocation values are excluded because their profiling hooks retained mock call histories; deterministic counters are retained, and allocation comparisons use the final shared hooks. The executable drivers are [performance_benchmark.py](performance_benchmark.py) and [paired_benchmark.py](paired_benchmark.py).

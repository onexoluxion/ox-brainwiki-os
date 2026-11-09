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

## Controls and limits

- Sequential samples drifted substantially even for identical listing code. All sequential samples are retained alongside the alternating confirmation. The first candidate's larger cursor batches missed the frozen allocation target; the final implementation uses 64-row batches and releases each drained batch before fetching another.
- Tail latency is not uniformly better. In alternating trials, new-process status at 100 documents had a 4.3% higher median and a 12.1% higher observed maximum; completeness at 1,000 documents had a 9.2% lower median but a 20.5% higher maximum. Exact search at 10 documents also had a higher maximum despite its lower median. No universal tail/startup improvement is claimed. With seven samples, the reported p95 is the observed maximum, not a population estimate.
- The initial approximately 4 KiB/document first-index pilot timed out at 1,000 documents under the existing 300-second backend limit. This failed preparation is retained as an unscored capacity observation. The successful comparison uses a separate short-note corpus and does not resolve that failed capacity case.
- Completeness measures index coverage, not relevance. Semantic requests still start a backend subprocess and retain both freshness checks. No model/dependency upgrade, persistent runtime cache, worker or watcher was introduced.

The design, frozen targets and review boundaries are in [PERFORMANCE_DESIGN.md](PERFORMANCE_DESIGN.md). The executable drivers are [performance_benchmark.py](performance_benchmark.py) and [paired_benchmark.py](paired_benchmark.py).

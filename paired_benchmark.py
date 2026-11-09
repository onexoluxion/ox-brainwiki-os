"""Alternate trusted implementations on identical synthetic state to limit time drift."""
import argparse
import hashlib
import importlib
import json
from pathlib import Path
import statistics
import subprocess
import sys
import time

import performance_benchmark as benchmark


def worker(code_root, workspace, size, semantic_only=False):
    sys.path.insert(0, str(code_root))
    runtime = importlib.import_module('ox_retrieval')
    for name in ('ox_retrieval', 'index_health', 'runtime_receipt', 'state_guard'):
        assert Path(importlib.import_module(name).__file__).parent == code_root
    benchmark.verify_workspace(runtime, workspace)
    root, state = benchmark.corpus(workspace, size)
    app = runtime.Retrieval(root, state)
    assert app.status()['fresh']
    hashes = app.inventory()
    def database_hash():
        with app.state_guard(), (state/'bm/memory.db').open('rb') as stream:
            return hashlib.file_digest(stream, 'sha256').hexdigest()
    before = database_hash()
    def completeness():
        with app.state_guard():
            return runtime.inspect_index(state/'bm/memory.db', state/'staging', hashes)
    def fresh_cli():
        result = subprocess.run([sys.executable, str(code_root/'ox_retrieval.py'),
                                 'status', '--config', str(workspace/str(size)/'config.json')],
                                check=True, capture_output=True, timeout=300)
        value = json.loads(result.stdout)
        assert value['fresh']
        return value
    operations = {
        'list': app.list,
        'exact': lambda: app.search('PERF-TARGET', mode='exact'),
        'status': app.status,
        'completeness': completeness,
        'new_process_status': fresh_cli,
    }
    if semantic_only:
        operations = {'semantic': lambda: app.search(
            'Why was the aurora calibration postponed?', scope='notes/target')}
    records = []
    for name, operation in operations.items():
        started = time.perf_counter()
        value = operation()
        elapsed = (time.perf_counter()-started)*1000
        records.append({'operation': name, 'elapsed_ms': round(elapsed, 3),
                        'result_signature': benchmark.signature(value)})
    assert database_hash() == before
    assert app.inventory() == hashes
    return {'size': size, 'input_index_sha256': before, 'records': records,
            'provenance': benchmark.provenance(runtime, code_root, workspace)}


def paired(baseline, candidate, workspace, pairs, semantic_only=False):
    trials = []
    for size in benchmark.SIZES:
        for number in range(pairs):
            order = ('baseline', 'candidate') if number % 2 == 0 else ('candidate', 'baseline')
            for label in order:
                code_root = baseline if label == 'baseline' else candidate
                command = [
                    sys.executable, str(Path(__file__).absolute()), '--worker',
                    '--code-root', str(code_root), '--workspace', str(workspace), '--size', str(size),
                ]
                if semantic_only:
                    command.append('--semantic-only')
                result = subprocess.run(command, capture_output=True, check=True, timeout=300)
                if len(result.stdout) > 4*1024*1024:
                    raise ValueError('worker output limit')
                trial = json.loads(result.stdout)
                trial.update(label=label, pair=number, order=list(order))
                trials.append(trial)
            print(json.dumps({'size': size, 'completed_pairs': number+1}), flush=True)
    summaries = []
    for size in benchmark.SIZES:
        selected = [t for t in trials if t['size'] == size]
        assert len({t['input_index_sha256'] for t in selected}) == 1
        assert len({json.dumps(t['provenance']['dependencies'], sort_keys=True) for t in selected}) == 1
        assert len({json.dumps(t['provenance']['model_files_sha256'], sort_keys=True) for t in selected}) == 1
        assert len({json.dumps(t['provenance']['corpora_sha256'], sort_keys=True) for t in selected}) == 1
        for operation in selected[0]['records']:
            name = operation['operation']
            rows = [(t['label'], r) for t in selected for r in t['records'] if r['operation'] == name]
            assert len({r['result_signature'] for _, r in rows}) == 1
            summary = {'size': size, 'operation': name}
            for label in ('baseline', 'candidate'):
                samples = [r['elapsed_ms'] for owner, r in rows if owner == label]
                assert len(samples) == pairs
                summary[label] = {'samples_ms': samples, 'p50_ms': statistics.median(samples),
                                  'p95_ms': max(samples)}
            summaries.append(summary)
    return {'schema': 1, 'condition': 'alternating fresh worker processes; direct calls after health/inventory checks',
            'pairs': pairs, 'operations': 'semantic' if semantic_only else 'read controls',
            'p95_definition': f'observed maximum for {pairs} samples',
            'paired_driver_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'trials': trials, 'summaries': summaries}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline-code-root', type=Path)
    parser.add_argument('--candidate-code-root', type=Path)
    parser.add_argument('--workspace', type=Path, required=True)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--worker', action='store_true')
    parser.add_argument('--code-root', type=Path)
    parser.add_argument('--size', type=int, choices=benchmark.SIZES)
    parser.add_argument('--semantic-only', action='store_true')
    parser.add_argument('--pairs', type=int, choices=(3, 7), default=7)
    args = parser.parse_args()
    if args.worker:
        if args.code_root is None or args.size is None:
            parser.error('worker requires an implementation and size')
        print(json.dumps(worker(args.code_root.absolute(), args.workspace.absolute(), args.size,
                                args.semantic_only)))
        return
    if args.baseline_code_root is None or args.candidate_code_root is None or args.output is None:
        parser.error('require baseline/candidate implementations and a new output path')
    if args.output.exists():
        parser.error('output already exists')
    report = paired(args.baseline_code_root.absolute(), args.candidate_code_root.absolute(),
                    args.workspace.absolute(), args.pairs, args.semantic_only)
    with args.output.open('x', encoding='utf-8') as stream:
        json.dump(report, stream, indent=2)
        stream.write('\n')


if __name__ == '__main__':
    main()

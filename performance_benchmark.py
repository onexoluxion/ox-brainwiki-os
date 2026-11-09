"""Synthetic-only benchmark driver shared by frozen baseline and candidate code."""
import argparse
from contextlib import contextmanager
import hashlib
import importlib
from importlib.metadata import version
import json
from pathlib import Path
import shutil
import statistics
import subprocess
import sys
import threading
import time
import tracemalloc
from unittest.mock import patch

import psutil

SIZES = (10, 100, 1000)
REPETITIONS = 2
TEXT = ('The invented calibration station records a reference reading, verifies the '
        'alignment and repeats the controlled procedure. ')


def fixture_bytes(number):
    header = ('# PERF-TARGET\nThe aurora calibration was postponed because the reference lamp failed.\n'
              if number == 0 else f'# Invented station {number}\n')
    return (header + TEXT*REPETITIONS + '\n').encode('utf-8')


def signature(value):
    def stable(item):
        if isinstance(item, dict):
            return {k: stable(v) for k, v in item.items()
                    if k not in ('source_mtime', 'indexed_at', 'last_error')}
        if isinstance(item, list):
            return [stable(v) for v in item]
        return item
    return hashlib.sha256(json.dumps(stable(value), sort_keys=True).encode()).hexdigest()


def corpus(workspace, size):
    return workspace/str(size)/'source', workspace/str(size)/'state'


def prepare(runtime, workspace, cache_state):
    if not cache_state.is_dir() or not (cache_state/'models').is_dir():
        raise ValueError('selected model cache must already exist')
    workspace.mkdir(parents=True, exist_ok=False)
    (workspace/'synthetic.json').write_text(json.dumps({'schema': 2, 'sizes': list(SIZES), 'repetitions': REPETITIONS}))
    cached = runtime.Retrieval(root=runtime.BASE/'fixtures', state=cache_state)
    for size in SIZES:
        root, state = corpus(workspace, size)
        for directory in ('notes/target', 'notes/other', 'notes/private'):
            (root/directory).mkdir(parents=True)
        for number in range(size):
            name = 'notes/target/answer.md' if number == 0 else f'notes/other/item-{number:04d}.md'
            (root/name).write_bytes(fixture_bytes(number))
        (root/'notes/private/excluded.md').write_text('EXCLUDED-PERF-FIXTURE', encoding='utf-8')
        app = runtime.Retrieval(root, state)
        with cached.state_guard(), app.state_guard():
            shutil.copytree(cache_state/'models', state/'models', symlinks=True)
        assert app.index()['fresh']
        config = workspace/str(size)/'config.json'
        config.write_text(json.dumps({'root': str(root), 'state': str(state),
                                      'allow': ['notes'], 'exclude': ['notes/private']}))
        print(json.dumps({'prepared_documents': size}), flush=True)


def verify_workspace(runtime, workspace):
    marker = workspace/'synthetic.json'
    with marker.open('rb') as stream:
        raw = stream.read(4097)
    if len(raw) > 4096 or json.loads(raw) != {'schema': 2, 'sizes': list(SIZES), 'repetitions': REPETITIONS}:
        raise ValueError('not a prepared synthetic benchmark workspace')
    for size in SIZES:
        root, state = corpus(workspace, size)
        if not state.is_dir():
            raise ValueError('prepared benchmark state is missing')
        expected = {'notes/target/answer.md': fixture_bytes(0),
                    **{f'notes/other/item-{n:04d}.md': fixture_bytes(n) for n in range(1,size)},
                    'notes/private/excluded.md': b'EXCLUDED-PERF-FIXTURE'}
        with runtime.pinned_directories(root):
            actual = set()
            for visited, entry in enumerate(root.rglob('*'), 1):
                if visited > 10000:
                    raise ValueError('benchmark traversal limit exceeded')
                if entry.is_symlink() or entry.is_junction():
                    raise ValueError('linked benchmark source denied')
                if entry.is_file():
                    if entry.stat().st_nlink != 1:
                        raise ValueError('linked benchmark source denied')
                    actual.add(entry.relative_to(root).as_posix())
                if len(actual) > size+1:
                    raise ValueError('unexpected benchmark source')
            if actual != expected.keys():
                raise ValueError('unexpected benchmark source')
            verifier = runtime.Retrieval(root, state, excluded=())
            for name, content in expected.items():
                if verifier.read(name)['sha256'] != hashlib.sha256(content).hexdigest():
                    raise ValueError('benchmark corpus is not synthetic')
        config = workspace/str(size)/'config.json'
        if config.is_symlink() or config.stat().st_nlink != 1 or config.stat().st_size > 4096:
            raise ValueError('invalid benchmark configuration')
        parsed = json.loads(config.read_text())
        if parsed != {'root': str(root), 'state': str(state), 'allow': ['notes'], 'exclude': ['notes/private']}:
            raise ValueError('benchmark configuration does not match its fixture')


def provenance(runtime, code_root, workspace):
    files = ('ox_retrieval.py', 'index_health.py', 'runtime_receipt.py', 'state_guard.py')
    app = runtime.Retrieval(*corpus(workspace, SIZES[0]))
    with app.state_guard():
        identity = app.identity()
    return {
        'benchmark_driver_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'runtime_files_sha256': {name: hashlib.sha256((code_root/name).read_bytes()).hexdigest() for name in files},
        'dependencies': {name: version(name) for name in ('basic-memory','fastmcp','fastembed','sqlite-vec','psutil')},
        'model_files_sha256': {name: digest for name,digest in identity.items() if name.startswith('models/')},
        'corpora_sha256': {str(size): hashlib.sha256(b''.join(fixture_bytes(n) for n in range(size))).hexdigest()
                           for size in SIZES},
    }


@contextmanager
def resources(app, runtime):
    counters = {'source_reads': 0, 'source_bytes': 0, 'staged_writes': 0,
                'staged_bytes': 0, 'inventory_calls': 0, 'backend_calls': 0,
                'backend_ms': 0.0, 'completeness_calls': 0, 'completeness_ms': 0.0}
    original_read, original_inventory = app.read, app.inventory
    original_backend, original_health = app.backend, runtime.inspect_index
    original_write = Path.write_bytes
    stage = app.state/'staging'
    def read(*args, **kwargs):
        result = original_read(*args, **kwargs)
        counters['source_reads'] += 1
        counters['source_bytes'] += len(result['content'].encode('utf-8'))
        return result
    def inventory(*args, **kwargs):
        counters['inventory_calls'] += 1
        return original_inventory(*args, **kwargs)
    def backend(*args, **kwargs):
        counters['backend_calls'] += 1
        started = time.perf_counter()
        try:
            return original_backend(*args, **kwargs)
        finally:
            counters['backend_ms'] += (time.perf_counter()-started)*1000
    def health(*args, **kwargs):
        counters['completeness_calls'] += 1
        started = time.perf_counter()
        try:
            return original_health(*args, **kwargs)
        finally:
            counters['completeness_ms'] += (time.perf_counter()-started)*1000
    def write(path, data):
        if path.is_relative_to(stage):
            counters['staged_writes'] += 1
            counters['staged_bytes'] += len(data)
        return original_write(path, data)
    stop = threading.Event()
    process = psutil.Process()
    peak = [0]
    def sample():
        while not stop.is_set():
            total = 0
            try:
                family = [process, *process.children(recursive=True)]
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                family = [process]
            for child in family:
                try:
                    total += child.memory_info().rss
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            peak[0] = max(peak[0], total)
            stop.wait(.01)
    sampler = threading.Thread(target=sample, daemon=True)
    with patch.object(app, 'read', read), patch.object(app, 'inventory', inventory), \
            patch.object(app, 'backend', backend), \
            patch.object(runtime, 'inspect_index', health), \
            patch.object(Path, 'write_bytes', write):
        tracemalloc.start()
        sampler.start()
        try:
            yield counters
        finally:
            stop.set()
            sampler.join(timeout=5)
            _, allocated = tracemalloc.get_traced_memory()
            tracemalloc.stop()
            counters['python_peak_kib'] = round(allocated/1024, 2)
            counters['sampled_tree_rss_kib'] = round(peak[0]/1024, 2)


def timed(operation, samples):
    elapsed, digests = [], set()
    for _ in range(samples):
        started = time.perf_counter()
        result = operation()
        elapsed.append((time.perf_counter()-started)*1000)
        digests.add(signature(result))
    assert len(digests) == 1, 'operation output changed across identical trials'
    ordered = sorted(elapsed)
    return {'samples_ms': [round(v, 3) for v in elapsed],
            'p50_ms': round(statistics.median(elapsed), 3),
            'p95_ms': round(ordered[min(len(ordered)-1, int(.95*len(ordered)))], 3),
            'result_signature': next(iter(digests))}


def measure(runtime, code_root, workspace, label, runs, only=None):
    records = []
    for size in SIZES:
        root, state = corpus(workspace, size)
        app = runtime.Retrieval(root, state)
        assert app.status()['fresh']
        original = app.inventory()
        with app.state_guard(), (state/'bm'/'memory.db').open('rb') as stream:
            input_index_hash = hashlib.file_digest(stream, 'sha256').hexdigest()
        operations = {
            'list': lambda: app.list(),
            'exact': lambda: app.search('PERF-TARGET', mode='exact'),
            'status': app.status,
            'semantic': lambda: app.search('Why was the aurora calibration postponed?',
                                          scope='notes/target'),
        }
        def completeness():
            with app.state_guard():
                return runtime.inspect_index(state/'bm'/'memory.db', state/'staging', original)
        operations['completeness'] = completeness
        config = workspace/str(size)/'config.json'
        def fresh_cli():
            result = subprocess.run([sys.executable, str(code_root/'ox_retrieval.py'),
                                     'status', '--config', str(config)],
                                    check=True, capture_output=True, timeout=300)
            value = json.loads(result.stdout)
            assert value['fresh']
            return value
        operations['new_process_status'] = fresh_cli
        if only is not None:
            operations = {name: operation for name, operation in operations.items() if name in only}
        for name, operation in operations.items():
            first_started = time.perf_counter()
            operation()
            first_ms = (time.perf_counter()-first_started)*1000
            result = timed(operation, min(runs, 3) if name == 'semantic' else runs)
            with resources(app, runtime) as counts:
                operation()
            record = dict(size=size, operation=name, first_call_ms=round(first_ms, 3),
                          **result, resources=counts, input_index_sha256=input_index_hash)
            records.append(record)
            print(json.dumps({'label': label, 'size': size, 'operation': name,
                              'p50_ms': result['p50_ms']}), flush=True)
        if only is not None and not {'unchanged_index', 'one_edit_restore_pair'} & set(only):
            assert app.inventory() == original
            continue
        # Warm up staging separately; repeated index still runs the real backend/probe.
        assert app.index()['fresh']
        if only is None or 'unchanged_index' in only:
            result = timed(app.index, 2)
            with resources(app, runtime) as counts:
                app.index()
            records.append(dict(size=size, operation='unchanged_index', **result, resources=counts))
        target = root/'notes/target/answer.md'
        saved = target.read_bytes()
        def one_edit():
            target.write_bytes(saved + b'\nOne invented revision.\n')
            try:
                result = app.index()
                assert result['fresh']
            finally:
                target.write_bytes(saved)
            assert app.index()['fresh']
            return result
        # This measures the edit-and-restore pair, so both versions start identically.
        if only is None or 'one_edit_restore_pair' in only:
            result = timed(one_edit, 2)
            with resources(app, runtime) as counts:
                one_edit()
            records.append(dict(size=size, operation='one_edit_restore_pair', **result, resources=counts))
        assert app.inventory() == original
        print(json.dumps({'label': label, 'size': size, 'index_cases': 'complete'}), flush=True)
    return {'schema': 1, 'label': label, 'python': sys.version.split()[0],
            'platform': 'Windows', 'condition': 'prepopulated model cache; repeated direct runtime calls',
            'fixture_repetitions': REPETITIONS,
            'rss_sampling_ms': 10, 'timings_exclude_resource_instrumentation': True,
            'counter_scope': 'in-process wrapper reads/writes/calls; excludes child file I/O',
            'rss_scope': 'sampled sum of process and descendant RSS; not unique physical memory',
            'provenance': provenance(runtime, code_root, workspace), 'records': records}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--code-root', required=True, type=Path)
    parser.add_argument('--workspace', required=True, type=Path)
    parser.add_argument('--cache-state', type=Path)
    parser.add_argument('--prepare', action='store_true')
    parser.add_argument('--label', choices=('baseline', 'candidate'), required=True)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--runs', type=int, choices=range(3, 8), default=5)
    parser.add_argument('--only', nargs='+', choices=('list', 'exact', 'status', 'semantic',
                        'new_process_status', 'completeness', 'unchanged_index', 'one_edit_restore_pair'))
    args = parser.parse_args()
    if args.output.exists():
        parser.error('output already exists; choose a new result path')
    code_root = args.code_root.absolute()
    sys.path.insert(0, str(code_root))
    runtime = importlib.import_module('ox_retrieval')
    assert Path(runtime.__file__).parent == code_root
    for name in ('index_health', 'runtime_receipt', 'state_guard'):
        assert Path(importlib.import_module(name).__file__).parent == code_root
    workspace = args.workspace.absolute()
    if args.prepare:
        if args.cache_state is None:
            parser.error('preparation requires the explicitly selected public model cache state')
        prepare(runtime, workspace, args.cache_state.absolute())
    verify_workspace(runtime, workspace)
    report = measure(runtime, code_root, workspace, args.label, args.runs, args.only)
    with args.output.open('x', encoding='utf-8') as stream:
        json.dump(report, stream, indent=2)
        stream.write('\n')


if __name__ == '__main__':
    main()

"""Synthetic benchmark admission and performance-regression safety cases."""
from concurrent.futures import ThreadPoolExecutor
import ctypes
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import ox_retrieval as runtime
import performance_benchmark as benchmark
import index_health
from test_runtime import make_app, database


class BenchmarkAdmission(unittest.TestCase):
    def fixture(self, workspace):
        workspace.mkdir()
        (workspace/'synthetic.json').write_text(json.dumps({
            'schema': 2, 'sizes': [1], 'repetitions': benchmark.REPETITIONS}))
        root, state = benchmark.corpus(workspace, 1)
        (root/'notes/target').mkdir(parents=True)
        (root/'notes/private').mkdir()
        state.mkdir()
        (root/'notes/target/answer.md').write_bytes(benchmark.fixture_bytes(0))
        (root/'notes/private/excluded.md').write_bytes(b'EXCLUDED-PERF-FIXTURE')
        (workspace/'1/config.json').write_text(json.dumps({
            'root': str(root), 'state': str(state), 'allow': ['notes'], 'exclude': ['notes/private']}))
        return root, state

    def test_exact_synthetic_fixture_is_admitted(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(benchmark, 'SIZES', (1,)):
            workspace = Path(tmp)/'fixture'
            self.fixture(workspace)
            benchmark.verify_workspace(runtime, workspace)

    def test_unknown_files_are_rejected_before_content_reads(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(benchmark, 'SIZES', (1,)):
            workspace = Path(tmp)/'fixture'
            root, _ = self.fixture(workspace)
            (root/'notes/unexpected.md').write_text('invented unexpected content')
            with patch.object(runtime.Retrieval, 'read') as read:
                with self.assertRaises(ValueError):
                    benchmark.verify_workspace(runtime, workspace)
                read.assert_not_called()

    def test_changed_source_or_config_is_not_admitted(self):
        for mutation in ('source', 'config'):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as tmp, \
                    patch.object(benchmark, 'SIZES', (1,)):
                workspace = Path(tmp)/'fixture'
                root, _ = self.fixture(workspace)
                if mutation == 'source':
                    (root/'notes/target/answer.md').write_text('different invented text')
                else:
                    (workspace/'1/config.json').write_text('{}')
                with self.assertRaises(ValueError):
                    benchmark.verify_workspace(runtime, workspace)

    def test_missing_cache_never_creates_cache_or_workspace(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache = Path(tmp)/'missing-cache'
            workspace = Path(tmp)/'fixture'
            with self.assertRaises(ValueError):
                benchmark.prepare(runtime, workspace, cache)
            self.assertFalse(cache.exists())
            self.assertFalse(workspace.exists())


class PerformanceSafety(unittest.TestCase):
    def test_exact_fuses_reads_but_drains_all_sources_and_keeps_final_status(self):
        with tempfile.TemporaryDirectory() as tmp:
            app = make_app(tmp)
            for n in range(8):
                (app.root/f'notes/other-{n}.md').write_text('SYN-471 invented match')
            original_read = app.read
            reads = []
            def read(name):
                reads.append(name)
                return original_read(name)
            with patch.object(app, 'read', read), patch.object(app, 'status', return_value={'fresh': False}) as status:
                found = app.search('syn-471', mode='exact', limit=1)
            self.assertEqual(len(reads), 9)
            self.assertEqual(len(found['results']), 1)
            status.assert_called_once()
            # An early match must not hide a later oversized source.
            (app.root/'notes/target/oversized.md').write_bytes(b'x'*(runtime.MAX_BYTES+1))
            with self.assertRaises(ValueError):
                app.search('SYN-471', mode='exact', limit=1)

    def test_overlapping_scope_does_not_duplicate_exact_results(self):
        with tempfile.TemporaryDirectory() as tmp:
            app = make_app(tmp)
            app.allowed = ('notes', 'notes/target')
            self.assertEqual(len(app.search('SYN-471', mode='exact')['results']), 1)

    def test_identical_index_staging_skips_writes_but_not_backend_work(self):
        with tempfile.TemporaryDirectory() as tmp:
            app = make_app(tmp)
            with patch.object(app, 'backend', return_value='') as backend, \
                    patch.object(app, 'backend_results', return_value=[]) as probe:
                self.assertTrue(app.index()['fresh'])
                writes = []
                original_write = Path.write_bytes
                def write(path, data):
                    writes.append(path)
                    return original_write(path, data)
                with patch.object(Path, 'write_bytes', write):
                    self.assertTrue(app.index()['fresh'])
                self.assertEqual(writes, [])
                self.assertEqual(backend.call_count, 2)
                self.assertEqual(probe.call_count, 2)
                staged = app.state/'staging/notes/target/answer.md'
                saved = staged.read_bytes()
                stat = staged.stat()
                os.utime(staged, ns=(stat.st_atime_ns, stat.st_mtime_ns-1000000))
                with patch.object(Path, 'write_bytes', write):
                    self.assertTrue(app.index()['fresh'])
                self.assertEqual(writes, [])
                staged.write_bytes(b'z'*len(saved))
                os.utime(staged, ns=(stat.st_atime_ns, stat.st_mtime_ns))
                self.assertTrue(app.index()['fresh'])
                self.assertEqual(staged.read_bytes(), saved)
                staged.write_bytes(b'z'*(runtime.MAX_BYTES+1))
                self.assertTrue(app.index()['fresh'])
                self.assertEqual(staged.read_bytes(), saved)
                extra = staged.parent/'removed.md'
                extra.write_text('invented removed note')
                self.assertTrue(app.index()['fresh'])
                self.assertFalse(extra.exists())

    def test_hardlinked_stage_is_rejected_without_changing_other_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            app = make_app(tmp)
            staged = app.state/'staging/notes/target/answer.md'
            staged.parent.mkdir(parents=True)
            other = Path(tmp)/'other.md'
            other.write_bytes(b'invented other file')
            staged.hardlink_to(other)
            with self.assertRaises((ValueError, OSError)):
                app.index()
            self.assertEqual(other.read_bytes(), b'invented other file')

    def test_source_change_during_staging_still_rejects_publication(self):
        with tempfile.TemporaryDirectory() as tmp:
            app = make_app(tmp)
            def changed(*args):
                (app.root/'notes/target/answer.md').write_text('changed invented source')
                return ''
            with patch.object(app, 'backend', side_effect=changed):
                with self.assertRaises(runtime.RuntimeFailure) as failure:
                    app.index()
            self.assertEqual(failure.exception.code, 'source_changed')
            self.assertFalse((app.state/'receipt.json').exists())

    def test_shared_win32_bindings_keep_concurrent_handles_local(self):
        with tempfile.TemporaryDirectory() as tmp:
            app = make_app(tmp)
            def read(_):
                for _ in range(20):
                    self.assertIn('SYN-471', app.read('notes/target/answer.md')['content'])
            with ThreadPoolExecutor(max_workers=4) as pool:
                list(pool.map(read, range(4)))
            moved = app.root.parent/'moved'
            app.root.rename(moved)
            moved.rename(app.root)

    def test_pin_failure_closes_handles_in_reverse_order(self):
        class API:
            def __init__(self):
                self.handles, self.closed = [], []
            def create(self, *args):
                handle = len(self.handles)+1
                self.handles.append(handle)
                return handle
            def close(self, handle):
                self.closed.append(handle)
            def info(self, handle, _, pointer, size):
                if handle == 2:
                    return 0
                ctypes.cast(pointer, ctypes.POINTER(runtime._AttributeTag)).contents.attributes = 0x10
                return 1
        api = API()
        with patch.object(runtime, '_WINDOWS', api), self.assertRaises(OSError):
            with runtime.pinned_directories(Path.cwd()):
                self.fail('failed pin entered context')
        self.assertEqual(api.closed, [2, 1])


class StreamingSafety(unittest.TestCase):
    def test_duplicate_filenames_and_extra_vectors_keep_incomplete_semantics(self):
        with tempfile.TemporaryDirectory() as tmp:
            app = make_app(tmp)
            hashes = app.inventory()
            with database(app) as db:
                db.execute('INSERT INTO entity SELECT 2, project_id, file_path, checksum, '
                           'vector_sync_deferred_at, sync_checksum FROM entity WHERE id=1')
                row = db.execute('SELECT embedding,source_hash FROM search_vector_embeddings WHERE rowid=1').fetchone()
                db.execute('INSERT INTO search_vector_embeddings(rowid,embedding,project_id,source_hash) VALUES(2,?,1,?)', row)
            result = index_health.inspect_index(app.state/'bm/memory.db', app.state/'staging', hashes)
            self.assertEqual(result['status'], 'incomplete')
            self.assertEqual(result['indexed_documents'], 2)
            self.assertEqual(result['extra_vectors'], 1)
            with patch.object(index_health, 'MAX_DOCUMENTS', 2):
                self.assertEqual(index_health.inspect_index(app.state/'bm/memory.db', app.state/'staging', hashes), result)
            with patch.object(index_health, 'MAX_DOCUMENTS', 1):
                self.assertEqual(index_health.inspect_index(app.state/'bm/memory.db', app.state/'staging', hashes)['reason'], 'index_limit')

    def test_real_rows_across_batch_boundary_and_each_limit(self):
        with tempfile.TemporaryDirectory() as tmp:
            app = make_app(tmp)
            hashes = app.inventory()
            with database(app) as db:
                row = db.execute('SELECT embedding, source_hash FROM search_vector_embeddings WHERE rowid=1').fetchone()
                for n in range(2, 7):
                    db.execute('INSERT INTO search_vector_chunks VALUES(?,1,1,?,?,?,?)',
                               (n, 'ready', index_health.EMBEDDING_IDENTITY, 'sqlite-vec', row[1]))
                    db.execute('INSERT INTO search_vector_embeddings(rowid,embedding,project_id,source_hash) VALUES(?,?,1,?)',
                               (n, row[0], row[1]))
            with patch.object(index_health, 'BATCH_ROWS', 2):
                result = index_health.inspect_index(app.state/'bm/memory.db', app.state/'staging', hashes)
                self.assertEqual(result['status'], 'complete')
                self.assertEqual(result['chunks'], 6)
                with patch.object(index_health, 'MAX_CHUNKS', 6):
                    self.assertEqual(index_health.inspect_index(app.state/'bm/memory.db', app.state/'staging', hashes), result)
                with patch.object(index_health, 'MAX_CHUNKS', 5):
                    limited = index_health.inspect_index(app.state/'bm/memory.db', app.state/'staging', hashes)
                    self.assertEqual(limited['reason'], 'index_limit')
                    self.assertEqual(limited['chunks'], 0)
                with database(app) as db:
                    db.execute('DELETE FROM search_vector_embeddings WHERE rowid=6')
                result = index_health.inspect_index(app.state/'bm/memory.db', app.state/'staging', hashes)
                self.assertEqual(result['invalid_chunks'], 1)
                self.assertEqual(result['status'], 'incomplete')

    def test_partial_cursor_failure_never_returns_partial_counts(self):
        with tempfile.TemporaryDirectory() as tmp:
            app = make_app(tmp)
            original = index_health._rows
            def broken(cursor, limit, deadline):
                for row in original(cursor, limit, deadline):
                    yield row
                    raise index_health.sqlite3.OperationalError('invented cursor failure')
            with patch.object(index_health, '_rows', broken):
                result = index_health.inspect_index(app.state/'bm/memory.db', app.state/'staging', app.inventory())
            self.assertEqual(result['status'], 'unknown')
            self.assertEqual(result['indexed_documents'], 0)

    def test_deadline_checked_even_without_sql_progress_callback(self):
        with tempfile.TemporaryDirectory() as tmp:
            app = make_app(tmp)
            with patch.object(index_health, 'QUERY_SECONDS', -1), \
                    patch.object(index_health, 'PROGRESS_STEPS', 10**9):
                result = index_health.inspect_index(app.state/'bm/memory.db', app.state/'staging', app.inventory())
            self.assertEqual(result['status'], 'unknown')
            self.assertEqual(result['chunks'], 0)

    def test_deadline_expiring_after_a_batch_raises_instead_of_finishing(self):
        class Cursor:
            def fetchmany(self, size):
                return [(1,)]
        with patch.object(index_health.time, 'monotonic', side_effect=[0, 2]):
            rows = index_health._rows(Cursor(), 1000, 1)
            self.assertEqual(next(rows), (1,))
            with self.assertRaises(index_health.sqlite3.OperationalError):
                next(rows)


if __name__ == '__main__':
    unittest.main()

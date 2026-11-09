"""Synthetic failure and completeness regressions; no external corpus is used."""
from contextlib import contextmanager
import hashlib
from importlib.metadata import PackageNotFoundError
import json
from pathlib import Path
import sqlite3
import struct
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

import sqlite_vec
from index_health import EMBEDDING_IDENTITY, inspect_index
from ox_retrieval import Retrieval, RuntimeFailure, client_tool
from runtime_receipt import MAX_RECEIPT_BYTES, SCHEMA, read_receipt, write_receipt


@contextmanager
def database(app):
    with app.state_guard():
        db = sqlite3.connect(app.state/'bm'/'memory.db')
        try:
            db.enable_load_extension(True)
            sqlite_vec.load(db)
            db.enable_load_extension(False)
            yield db
            db.commit()
        finally:
            db.close()


def make_app(parent):
    root = Path(parent)/'source'
    (root/'notes'/'target').mkdir(parents=True)
    (root/'notes'/'target'/'answer.md').write_text('SYN-471 calibration protocol', encoding='utf-8')
    app = Retrieval(root, Path(parent)/'state')
    with app.state_guard():
        (app.state/'staging').mkdir()
        (app.state/'bm').mkdir()
        (app.state/'bm'/'config.json').write_text('{}')
        (app.state/'models').mkdir()
        (app.state/'models'/'model.onnx').write_bytes(b'synthetic artifact, not a model')
    digest = app.inventory()['notes/target/answer.md']
    with database(app) as db:
        db.executescript('''
            CREATE TABLE project(id INTEGER PRIMARY KEY, path TEXT);
            CREATE TABLE entity(id INTEGER PRIMARY KEY, project_id INTEGER,
                file_path TEXT, checksum TEXT, vector_sync_deferred_at TEXT, sync_checksum TEXT);
            CREATE TABLE search_vector_chunks(id INTEGER PRIMARY KEY, project_id INTEGER,
                entity_id INTEGER, embedding_status TEXT, embedding_model TEXT,
                vector_index TEXT, source_hash TEXT);
            CREATE VIRTUAL TABLE search_vector_embeddings USING vec0(
                embedding float[384], project_id integer partition key, +source_hash text);
        ''')
        db.execute('INSERT INTO project VALUES(?,?)', (1, str(app.state/'staging')))
        db.execute('INSERT INTO entity VALUES(1,1,?,?,NULL,?)', ('notes/target/answer.md', digest, digest))
        db.execute('INSERT INTO search_vector_chunks VALUES(1,1,1,?,?,?,?)',
                   ('ready', EMBEDDING_IDENTITY, 'sqlite-vec', digest))
        db.execute('INSERT INTO search_vector_embeddings(rowid,embedding,project_id,source_hash) '
                   'VALUES(1,?,1,?)', (struct.pack('384f', *([0.0]*384)), digest))
    publish(app)
    return app


def publish(app):
    with app.state_guard():
        write_receipt(app.state/'receipt.json', {
            'schema': SCHEMA, 'hashes': app.inventory(), 'identity': app.identity(),
            'indexed_at': time.time(), 'vector_probe': True,
        })


class Receipts(unittest.TestCase):
    def test_corrupt_receipts_are_stale_and_exact_remains_live(self):
        with tempfile.TemporaryDirectory() as tmp:
            app = make_app(tmp)
            for raw in (b'', b'{', b'[]', b'null', b'{}',
                        b'{"schema":1,"schema":1}', b'x'*(MAX_RECEIPT_BYTES+1)):
                with self.subTest(size=len(raw)):
                    (app.state/'receipt.json').write_bytes(raw)
                    state = app.status()
                    self.assertFalse(state['fresh'])
                    self.assertIn(state['reason'], ('receipt_invalid', 'receipt_oversized'))
                    self.assertTrue(app.search('SYN-471', mode='exact')['results'])
                    with self.assertRaises(RuntimeFailure) as error:
                        app.search('calibration')
                    self.assertEqual(error.exception.code, 'index_unavailable')

    def test_legacy_receipt_requires_rebuild(self):
        with tempfile.TemporaryDirectory() as tmp:
            app = make_app(tmp)
            path = app.state/'receipt.json'
            data = json.loads(path.read_text())
            del data['schema']
            path.write_text(json.dumps(data))
            self.assertEqual(app.status()['reason'], 'receipt_invalid')

    def test_atomic_replace_failure_preserves_original_and_cleans_temporary(self):
        with tempfile.TemporaryDirectory() as tmp:
            app = make_app(tmp)
            path = app.state/'receipt.json'
            before = path.read_bytes()
            data, _ = read_receipt(path)
            with patch('runtime_receipt.os.replace', side_effect=OSError('synthetic failure')):
                with self.assertRaises(OSError):
                    write_receipt(path, data)
            self.assertEqual(path.read_bytes(), before)
            self.assertEqual(list(app.state.glob('receipt-*.tmp')), [])

    def test_invalid_field_shapes_and_numbers_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            app = make_app(tmp)
            path = app.state/'receipt.json'
            original = json.loads(path.read_text())
            for key, value in [('schema', True), ('vector_probe', 1), ('hashes', []),
                               ('identity', {'unexpected': []}), ('indexed_at', float('nan')),
                               ('indexed_at', 10**1000)]:
                data = dict(original, **{key: value})
                path.write_text(json.dumps(data))
                self.assertFalse(app.status()['fresh'])


class Completeness(unittest.TestCase):
    def health(self, app):
        return inspect_index(app.state/'bm'/'memory.db', app.state/'staging', app.inventory())

    def test_complete_and_no_database_mutation(self):
        with tempfile.TemporaryDirectory() as tmp:
            app = make_app(tmp)
            path = app.state/'bm'/'memory.db'
            before = path.read_bytes()
            self.assertTrue(app.status()['fresh'])
            self.assertEqual(self.health(app)['status'], 'complete')
            self.assertEqual(path.read_bytes(), before)

    def test_missing_changed_unexpected_and_deferred_documents(self):
        statements = [
            ('DELETE FROM entity', 'missing_documents'),
            ("UPDATE entity SET checksum='wrong', sync_checksum='wrong'", 'changed_documents'),
            ("UPDATE entity SET file_path='notes/private/extra.md'", 'unexpected_documents'),
            ("UPDATE entity SET vector_sync_deferred_at='deferred'", 'incomplete_documents'),
        ]
        for statement, counter in statements:
            with self.subTest(counter=counter), tempfile.TemporaryDirectory() as tmp:
                app = make_app(tmp)
                with database(app) as db:
                    db.execute(statement)
                health = self.health(app)
                self.assertEqual(health['status'], 'incomplete')
                self.assertGreater(health[counter], 0)
                self.assertFalse(app.status()['fresh'])

    def test_missing_pending_wrong_model_and_stale_vectors(self):
        statements = [
            'DELETE FROM search_vector_embeddings WHERE rowid=1',
            "UPDATE search_vector_chunks SET embedding_status='pending'",
            "UPDATE search_vector_chunks SET embedding_model='unselected-model'",
            "UPDATE search_vector_chunks SET source_hash='different'",
            "UPDATE search_vector_chunks SET vector_index='unselected-store'",
            'DELETE FROM search_vector_chunks',
        ]
        for statement in statements:
            with self.subTest(statement=statement), tempfile.TemporaryDirectory() as tmp:
                app = make_app(tmp)
                with database(app) as db:
                    db.execute(statement)
                self.assertEqual(self.health(app)['status'], 'incomplete')
                self.assertFalse(app.status()['fresh'])

    def test_unavailable_unsupported_and_work_limits_are_unknown(self):
        with tempfile.TemporaryDirectory() as tmp:
            app = make_app(tmp)
            with patch('index_health.version', return_value='unsupported'):
                self.assertEqual(self.health(app)['reason'], 'unsupported_backend')
            with patch('index_health.MAX_DOCUMENTS', 0):
                self.assertEqual(self.health(app)['reason'], 'index_limit')
            with patch('index_health.QUERY_SECONDS', -1), patch('index_health.PROGRESS_STEPS', 1):
                self.assertEqual(self.health(app)['status'], 'unknown')
            (app.state/'bm'/'memory.db').write_bytes(b'not a database')
            self.assertEqual(self.health(app)['status'], 'unknown')

    def test_empty_document_can_have_no_chunks(self):
        with tempfile.TemporaryDirectory() as tmp:
            app = make_app(tmp)
            (app.root/'notes'/'empty.md').write_bytes(b'')
            with database(app) as db:
                db.execute('INSERT INTO entity VALUES(2,1,?,?,NULL,?)',
                           ('notes/empty.md', hashlib.sha256(b'').hexdigest(), hashlib.sha256(b'').hexdigest()))
            self.assertEqual(self.health(app)['status'], 'complete')

    def test_backend_normalized_frontmatter_retains_input_identity(self):
        with tempfile.TemporaryDirectory() as tmp:
            app = make_app(tmp)
            with database(app) as db:
                db.execute("UPDATE entity SET checksum=?", ('f'*64,))
            self.assertEqual(self.health(app)['status'], 'complete')

    def test_missing_package_metadata_is_unknown(self):
        with tempfile.TemporaryDirectory() as tmp:
            app = make_app(tmp)
            with patch('index_health.version', side_effect=PackageNotFoundError('synthetic')):
                self.assertEqual(self.health(app)['reason'], 'backend_metadata_unavailable')
            with patch('ox_retrieval.version', side_effect=PackageNotFoundError('synthetic')):
                state = app.status()
                self.assertFalse(state['fresh'])
                self.assertEqual(state['backend'], 'basic-memory unknown')

    def test_artifact_work_is_bounded(self):
        with tempfile.TemporaryDirectory() as tmp:
            app = make_app(tmp)
            (app.state/'models'/'extra.json').write_text('{}')
            for key in ('MAX_MODEL_ENTRIES', 'MAX_MODEL_FILES',
                        'MAX_ARTIFACT_FILE_BYTES', 'MAX_ARTIFACT_BYTES'):
                with self.subTest(limit=key), patch('ox_retrieval.'+key, 1):
                    self.assertIsNone(app.identity())
                    self.assertFalse(app.status()['fresh'])

    def test_forged_sync_field_cannot_refresh_existing_receipt(self):
        with tempfile.TemporaryDirectory() as tmp:
            app = make_app(tmp)
            with database(app) as db:
                db.execute('UPDATE entity SET checksum=?, sync_checksum=?',
                           ('e'*64, app.inventory()['notes/target/answer.md']))
            state = app.status()
            self.assertEqual(state['completeness']['status'], 'complete')
            self.assertFalse(state['fresh'])
            self.assertEqual(state['reason'], 'artifacts_changed')


class SearchAndErrors(unittest.TestCase):
    def test_client_boundary_never_exposes_state_exceptions(self):
        with tempfile.TemporaryDirectory() as tmp:
            app = make_app(tmp)
            with patch.object(app, '_read_pinned', side_effect=OSError('SYNTHETIC-INTERNAL-DETAIL')):
                with self.assertRaises(RuntimeFailure) as error:
                    client_tool(app, 'read')('notes/target/answer.md')
                self.assertEqual(error.exception.code, 'state_unavailable')
                self.assertNotIn('SYNTHETIC-INTERNAL-DETAIL', str(error.exception))
            with self.assertRaises(RuntimeFailure) as error:
                client_tool(app, 'read')('../outside.md')
            self.assertEqual(error.exception.code, 'invalid_request')

    def test_backend_directory_failure_uses_fixed_diagnostic(self):
        with tempfile.TemporaryDirectory() as tmp:
            app = make_app(tmp)
            with patch('ox_retrieval.Path.mkdir', side_effect=OSError('SYNTHETIC-INTERNAL-DETAIL')):
                with self.assertRaises(RuntimeFailure) as error:
                    app.backend('ignored')
                self.assertEqual(error.exception.code, 'backend_start_failed')
                self.assertNotIn('SYNTHETIC-INTERNAL-DETAIL', str(error.exception))

    def test_scope_is_applied_before_backend_limit(self):
        with tempfile.TemporaryDirectory() as tmp:
            app = make_app(tmp)
            expected = 'notes/target/answer.md'
            def backend(*args):
                # Simulates 60 globally higher-ranked, out-of-scope documents.
                paths = ([expected] if '--path' in args
                         and args[args.index('--path')+1] == 'notes/target'
                         else [f'notes/other/{i}.md' for i in range(50)])
                return json.dumps({'results': [{'file_path': p} for p in paths]})
            with patch.object(app, 'backend', side_effect=backend):
                result = app.search('calibration protocol', scope='notes/target')
            self.assertEqual(result['results'][0]['path'], expected)

    def test_source_mutation_during_search_rejects_response(self):
        with tempfile.TemporaryDirectory() as tmp:
            app = make_app(tmp)
            def backend(*args):
                (app.root/'notes/target/answer.md').write_text('Changed synthetic evidence')
                return json.dumps({'results': [{'file_path': 'notes/target/answer.md'}]})
            with patch.object(app, 'backend', side_effect=backend):
                with self.assertRaises(RuntimeFailure) as error:
                    app.search('calibration protocol')
            self.assertEqual(error.exception.code, 'source_changed')

    def test_invalid_backend_json_is_bounded_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            app = make_app(tmp)
            for raw in ('{', '[]', '{"results":{}}', '{"results":[null]}'):
                with patch.object(app, 'backend', return_value=raw):
                    with self.assertRaises(RuntimeFailure) as error:
                        app.search('calibration')
                    self.assertEqual(error.exception.code, 'backend_invalid_output')

    def test_diagnostics_distinguish_failures_without_echoing_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            app = make_app(tmp)
            app.exe = Path(sys.executable)
            cases = [
                ('import sys; print("SYNTHETIC-NOT-FOR-CLIENT"); sys.exit(7)', 'backend_exit'),
                ('import sys; sys.stdout.write("x"*5000000)', 'backend_output_limit'),
                ('import time; time.sleep(30)', 'backend_timeout'),
            ]
            for script, code in cases:
                app.backend_timeout = .2 if code == 'backend_timeout' else 10
                with self.assertRaises(RuntimeFailure) as error:
                    app.backend('-c', script)
                self.assertEqual(error.exception.code, code)
                state = app.status()
                self.assertEqual(state['last_error']['code'], code)
                self.assertNotIn('SYNTHETIC-NOT-FOR-CLIENT', str(error.exception))
                self.assertNotIn(str(app.root), json.dumps(state))
                self.assertNotIn(script, json.dumps(state))
            self.assertEqual(app.backend('-c', 'print("ok")').strip(), 'ok')
            self.assertIsNone(app.last_error)


if __name__ == '__main__':
    unittest.main()

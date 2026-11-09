import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from ox_retrieval import Retrieval

class Boundaries(unittest.TestCase):
    def setUp(self):
        self.r = Retrieval()
    def test_paths(self):
        for p in ['../secret.md','C:/secret.md','/etc/passwd','notes/../x.md','notes/private/hidden.md','notes/PRIVATE/hidden.md','notes/a.md:stream','notes\\a.md']:
            with self.subTest(p=p), self.assertRaises(ValueError):
                self.r.read(p)
    def test_exact_and_original(self):
        before = self.r.inventory()
        self.assertEqual(self.r.search('wo-2048','exact')['results'][0]['path'], 'notes/shipment.md')
        self.assertIn('drop test', self.r.read('notes/shipment.md')['content'])
        self.assertEqual(before,self.r.inventory())
        self.assertNotIn('notes/private/hidden.md',before)
    def test_limits(self):
        with self.assertRaises(ValueError): self.r.list(limit=51)
        with self.assertRaises(ValueError): self.r.search('x'*513)
    def test_link(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/'root'; (root/'notes').mkdir(parents=True)
            outside=Path(tmp)/'outside.md'; outside.write_text('outside')
            link=root/'notes'/'escape.md'
            try: link.symlink_to(outside)
            except OSError: self.skipTest('symlink privilege unavailable')
            r=Retrieval(root,Path(tmp)/'state')
            with self.assertRaises(ValueError): r.read('notes/escape.md')
            self.assertEqual(r.inventory(),{})

if __name__=='__main__': unittest.main()

class Hardening(unittest.TestCase):
    def test_aliases_all_operations(self):
        r = Retrieval()
        for path in ('notes/private./hidden.md', 'notes/private /hidden.md', 'notes/PRIVAT~1/hidden.md'):
            for call in (r.read, r.list, lambda p: r.search('x', 'exact', p)):
                with self.subTest(path=path), self.assertRaises(ValueError): call(path)

    def test_opened_object_validated(self):
        from unittest.mock import patch
        r = Retrieval()
        original = Path.open
        outside = r.root/'notes'/'private'/'hidden.md'
        def redirected(p, *args, **kwargs):
            return original(outside if p.name == 'shipment.md' else p, *args, **kwargs)
        with patch.object(Path, 'open', redirected), self.assertRaises(ValueError):
            r.read('notes/shipment.md')

    def test_identity_missing_replaced(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = Retrieval(state=Path(tmp)/'state')
            with r.state_guard():
                (r.state/'bm').mkdir()
                (r.state/'bm/config.json').write_text('{}')
                (r.state/'models').mkdir()
                (r.state/'models/test.onnx').write_bytes(b'synthetic model')
                db = r.state/'bm/memory.db'; db.write_bytes(b'first')
                receipt = {'hashes': r.inventory(), 'identity': r.identity(), 'vector_probe':True}
                from runtime_receipt import write_receipt, SCHEMA
                import time
                receipt.update(schema=SCHEMA, indexed_at=time.time())
                write_receipt(r.state/'receipt.json', receipt)
                # Isolate artifact-change detection; real SQLite parity has its own suite.
                with patch('ox_retrieval.inspect_index', return_value={'status':'complete', 'reason':'ready'}):
                    self.assertTrue(r.status()['fresh'])
                db.write_bytes(b'other')
                self.assertFalse(r.status()['fresh'])
                db.unlink()
                self.assertFalse(r.status()['fresh'])

    def test_hostile_environment(self):
        from unittest.mock import patch
        with patch.dict(os.environ, {'BASIC_MEMORY_DATABASE_URL':'hostile', 'HF_ENDPOINT':'hostile', 'PYTHONPATH':'hostile'}):
            env = Retrieval().env()
            for key in ('BASIC_MEMORY_DATABASE_URL','HF_ENDPOINT','PYTHONPATH'):
                self.assertNotIn(key, env)

class Configuration(unittest.TestCase):
    def test_schema_and_relative_paths(self):
        from ox_retrieval import load_config
        with tempfile.TemporaryDirectory() as tmp:
            config = Path(tmp)/'config.json'
            valid = {'root':'source','state':'index','allow':['notes'],'exclude':['notes/private']}
            config.write_text(json.dumps(valid))
            self.assertEqual(load_config(config)['root'], Path(tmp)/'source')
            for key, value in [('extra',1),('allow',[]),('exclude',['../outside']),('root',1),('allow','notes')]:
                config.write_text(json.dumps(dict(valid, **{key:value})))
                with self.subTest(key=key), self.assertRaises(ValueError): load_config(config)
            config.write_text('{"root":"a","root":"b"}')
            with self.assertRaises(ValueError): load_config(config)

class DirectoryPins(unittest.TestCase):
    def test_pinned_parent_cannot_be_renamed(self):
        from ox_retrieval import pinned_directories
        with tempfile.TemporaryDirectory() as tmp:
            parent = Path(tmp)/'source'; parent.mkdir()
            with pinned_directories(parent):
                with self.assertRaises(OSError): parent.rename(Path(tmp)/'moved')
            parent.rename(Path(tmp)/'moved')

    def test_real_junction_denied(self):
        import subprocess
        from ox_retrieval import pinned_directories
        with tempfile.TemporaryDirectory() as tmp:
            outside = Path(tmp)/'outside'; outside.mkdir()
            link = Path(tmp)/'junction'
            subprocess.run(['cmd','/c','mklink','/J',str(link),str(outside)],check=True,capture_output=True)
            try:
                with self.assertRaises(ValueError):
                    with pinned_directories(link): pass
            finally:
                link.rmdir()

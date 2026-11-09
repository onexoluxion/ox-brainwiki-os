import json, os, subprocess, sys, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
import win32api, win32security
from ox_retrieval import Retrieval, pinned_directories, RuntimeFailure
from state_guard import validate_acl

class DeploymentBoundaries(unittest.TestCase):
    def setup_app(self,tmp):
        root=Path(tmp)/'source';(root/'notes').mkdir(parents=True)
        (root/'notes/a.md').write_text('identifier and knowledge')
        return Retrieval(root,Path(tmp)/'state')

    def test_private_state_acl_and_exclusive_lock(self):
        with tempfile.TemporaryDirectory() as tmp:
            r=self.setup_app(tmp)
            with r.state_guard():
                validate_acl(r.state)
                with self.assertRaises(Exception):
                    with Retrieval(r.root,r.state).state_guard():pass
                with self.assertRaises(OSError):r.state.rename(Path(tmp)/'moved')
            with r.state_guard():pass

    def test_broad_state_rejected_without_acl_rewrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            r=self.setup_app(tmp);r.state.mkdir()
            before=win32security.ConvertSecurityDescriptorToStringSecurityDescriptor(win32security.GetFileSecurity(str(r.state),win32security.DACL_SECURITY_INFORMATION),1,win32security.DACL_SECURITY_INFORMATION)
            with self.assertRaises(ValueError):r.status()
            after=win32security.ConvertSecurityDescriptorToStringSecurityDescriptor(win32security.GetFileSecurity(str(r.state),win32security.DACL_SECURITY_INFORMATION),1,win32security.DACL_SECURITY_INFORMATION)
            self.assertEqual(before,after)

    def test_state_junction_no_external_write(self):
        with tempfile.TemporaryDirectory() as tmp:
            r=self.setup_app(tmp);outside=Path(tmp)/'outside';outside.mkdir()
            subprocess.run(['cmd','/c','mklink','/J',str(r.state),str(outside)],check=True,capture_output=True)
            try:
                with self.assertRaises(ValueError):r.index()
                self.assertEqual(list(outside.iterdir()),[])
            finally:r.state.rmdir()

    def test_source_junction_swap_between_validation_and_pin(self):
        with tempfile.TemporaryDirectory() as tmp:
            r=self.setup_app(tmp);outside=Path(tmp)/'outside';outside.mkdir();(outside/'a.md').write_text('SECRET')
            original=r.path;called=False
            def swap(name,directory=False):
                nonlocal called
                p=original(name,directory)
                if not called:
                    called=True;(r.root/'notes').rename(r.root/'saved')
                    subprocess.run(['cmd','/c','mklink','/J',str(r.root/'notes'),str(outside)],check=True,capture_output=True)
                return p
            try:
                with patch.object(r,'path',swap),self.assertRaises(ValueError):r.read('notes/a.md')
            finally:
                if (r.root/'notes').is_junction():(r.root/'notes').rmdir()
            self.assertEqual((outside/'a.md').read_text(),'SECRET')

    def test_actual_short_name_alias_denied(self):
        with tempfile.TemporaryDirectory() as tmp:
            r=self.setup_app(tmp);private=r.root/'notes'/'private long directory';private.mkdir();(private/'hidden.md').write_text('SECRET')
            r.excluded=('notes/private long directory',)
            short=Path(win32api.GetShortPathName(str(private)))
            if short.name==private.name:self.skipTest('volume does not allocate an 8.3 alias')
            for call in (r.read,r.list,lambda p:r.search('SECRET','exact',p)):
                with self.assertRaises(ValueError):call('notes/'+short.name+'/hidden.md')

    def test_failed_rebuild_invalidates_receipt(self):
        with tempfile.TemporaryDirectory() as tmp:
            r=self.setup_app(tmp)
            with r.state_guard():(r.state/'receipt.json').write_text('{}')
            with patch.object(r,'backend',side_effect=RuntimeError('interrupted')),self.assertRaises(RuntimeError):r.index()
            self.assertFalse((r.state/'receipt.json').exists())
            self.assertFalse(r.status()['fresh'])

    def test_model_and_config_changes_invalidate_identity(self):
        with tempfile.TemporaryDirectory() as tmp:
            r=self.setup_app(tmp)
            with r.state_guard():
                (r.state/'bm').mkdir();(r.state/'models').mkdir()
                (r.state/'bm/config.json').write_text('{}');(r.state/'bm/memory.db').write_bytes(b'db')
                model=r.state/'models/model.onnx';model.write_bytes(b'model')
                ident=r.identity();model.write_bytes(b'changed');self.assertNotEqual(ident,r.identity())
                model.unlink();self.assertIsNone(r.identity())

    def test_backend_output_and_timeout(self):
        with tempfile.TemporaryDirectory() as tmp:
            r=self.setup_app(tmp);r.exe=Path(sys.executable)
            with self.assertRaises(RuntimeError):r.backend('-c','import sys; sys.stdout.write("x"*5000000)')
            r.backend_timeout=.15
            with self.assertRaises(RuntimeError):r.backend('-c','import time; time.sleep(30)')
            self.assertEqual(r.backend('-c','print("ok")').strip(),'ok')

    def test_job_setup_failure_never_launches_child(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = self.setup_app(tmp)
            for target in ('CreateJobObject', 'QueryInformationJobObject', 'SetInformationJobObject'):
                with patch('ox_retrieval.win32job.' + target, side_effect=OSError('setup failed')):
                    with patch('ox_retrieval.subprocess.Popen') as launch:
                        with self.assertRaises(RuntimeFailure) as error:
                            r.backend('ignored')
                        self.assertEqual(error.exception.code, 'backend_start_failed')
                        launch.assert_not_called()

    def test_corpus_byte_budget(self):
        with tempfile.TemporaryDirectory() as tmp:
            r=self.setup_app(tmp)
            with patch('ox_retrieval.MAX_BYTES',32):
                (r.root/'notes/large.md').write_text('x'*33)
                with self.assertRaises(ValueError):r.inventory()

if __name__=='__main__':unittest.main()

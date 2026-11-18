"""Native macOS boundary regressions on disposable files."""
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from ox_retrieval import Retrieval


@unittest.skipUnless(sys.platform == 'darwin', 'macOS filesystem checks')
class MacBoundaries(unittest.TestCase):
    def setUp(self):
        sandbox = tempfile.TemporaryDirectory()
        self.addCleanup(sandbox.cleanup)
        self.parent = Path(sandbox.name).resolve()
        self.root = self.parent / 'vault'
        self.notes = self.root / 'notes'
        self.notes.mkdir(parents=True)
        (self.notes / 'answer.md').write_text('synthetic answer', encoding='utf-8')
        self.state = self.parent / 'state'
        self.app = Retrieval(self.root, self.state)

    def test_private_creation_and_exclusive_lock(self):
        with self.app.state_guard():
            self.assertEqual(stat.S_IMODE(self.state.stat().st_mode), 0o700)
            self.assertEqual(stat.S_IMODE((self.state / 'operation.lock').stat().st_mode), 0o600)
            with self.assertRaises(BlockingIOError):
                with Retrieval(self.root, self.state).state_guard():
                    self.fail('second state lock was granted')
        with self.app.state_guard():
            self.assertTrue(self.state.is_dir())

    def test_broad_existing_state_rejected_without_changing_mode(self):
        self.state.mkdir(mode=0o755)
        self.state.chmod(0o755)
        with self.assertRaises(ValueError):
            self.app.status()
        self.assertEqual(stat.S_IMODE(self.state.stat().st_mode), 0o755)
        self.assertFalse((self.state / 'operation.lock').exists())

    def test_acl_grant_is_rejected_even_with_private_mode(self):
        self.state.mkdir(mode=0o700)
        subprocess.run(['/bin/chmod', '+a', 'everyone allow list,search', str(self.state)],
                       check=True, capture_output=True)
        with self.assertRaises(ValueError):
            self.app.status()
        self.assertFalse((self.state / 'operation.lock').exists())

    def test_linked_state_cannot_write_outside(self):
        outside = self.parent / 'elsewhere'
        outside.mkdir()
        self.state.symlink_to(outside, target_is_directory=True)
        with self.assertRaises((OSError, ValueError)):
            self.app.index()
        self.assertEqual(list(outside.iterdir()), [])

    def test_source_swap_at_open_is_rejected(self):
        outside = self.parent / 'outside.md'
        outside.write_text('excluded', encoding='utf-8')
        target = self.notes / 'answer.md'
        original_open = os.open

        def swap(path, flags, *args, **kwargs):
            if path == target:
                target.unlink()
                target.symlink_to(outside)
            return original_open(path, flags, *args, **kwargs)

        with patch('macos_guard.os.open', side_effect=swap), self.assertRaises((OSError, ValueError)):
            self.app.read('notes/answer.md')

    def test_hardlinked_source_and_unicode_exclusion(self):
        excluded = self.notes / 'caf\u00e9'
        excluded.mkdir()
        note = excluded / 'secret.md'
        note.write_text('excluded', encoding='utf-8')
        (self.notes / 'alias.md').hardlink_to(note)
        app = Retrieval(self.root, self.state, excluded=('notes/caf\u00e9',))
        for path in ('notes/cafe\u0301/secret.md', 'notes/alias.md'):
            with self.subTest(path=path), self.assertRaises(ValueError):
                app.read(path)

    def test_backend_reaps_processes_that_hold_stdout(self):
        self.app.exe = Path(sys.executable)
        code = ('import subprocess, sys; '
                'subprocess.Popen([sys.executable, "-c", "import time;time.sleep(30)"]); '
                'print("done", flush=True)')
        self.app.backend_timeout = 3
        self.assertEqual(self.app.backend('-c', code).strip(), 'done')

    def test_backend_inherits_the_state_lock(self):
        self.app.exe = Path(sys.executable)
        with self.app.state_guard():
            fd = self.app._guard_local.lock
            code = 'import os, sys; print(os.fstat(int(sys.argv[1])).st_ino)'
            inode = self.app.backend('-c', code, str(fd)).strip()
            self.assertEqual(inode, str((self.state / 'operation.lock').stat().st_ino))

from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import ox_retrieval
from ox_retrieval import Retrieval, WINDOWS_MAX_PATH, MODEL_PATH_SUFFIX

LIMIT = WINDOWS_MAX_PATH - MODEL_PATH_SUFFIX
MESSAGE = 'state path too long'

def long_state(tmp):
    """A state path under tmp whose absolute length exceeds the guard limit; its parent exists."""
    state = Path(tmp).absolute() / 'parent' / ('s' * max(1, LIMIT + 1 - len(str(Path(tmp).absolute() / 'parent')) - 1))
    state.parent.mkdir()
    assert len(str(state)) > LIMIT
    return state

class PathLength(unittest.TestCase):
    def test_long_state_rejected_without_long_paths(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(ox_retrieval, 'long_paths_enabled', return_value=False):
            state = long_state(tmp)
            with self.assertRaises(ValueError) as caught:
                Retrieval(state=state)
            self.assertIn(MESSAGE, str(caught.exception))
            self.assertIn(f'{len(str(state))} characters, limit {LIMIT}', str(caught.exception))
            self.assertFalse(state.exists())

    def test_long_state_passes_guard_with_long_paths(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(ox_retrieval, 'long_paths_enabled', return_value=True):
            state = long_state(tmp)
            try:
                Retrieval(state=state)
            except Exception as error:
                self.assertNotIn(MESSAGE, str(error))

    def test_short_state_never_rejected(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(ox_retrieval, 'long_paths_enabled', return_value=False):
            state = Path(tmp).absolute() / 'state'
            self.assertLessEqual(len(str(state)), LIMIT)
            try:
                Retrieval(state=state)
            except Exception as error:
                self.assertNotIn(MESSAGE, str(error))

    def test_long_paths_enabled_reads_registry_or_false(self):
        self.assertIn(ox_retrieval.long_paths_enabled(), (True, False))
        with patch.object(ox_retrieval.winreg, 'OpenKey', side_effect=OSError('missing')):
            self.assertFalse(ox_retrieval.long_paths_enabled())

if __name__ == '__main__':
    unittest.main()

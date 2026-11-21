"""Automatic-indexing regressions on disposable files; the OS job and backend are stubbed here.

schedule_acceptance.py covers the real scheduler and backend.
"""
from contextlib import contextmanager
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET

import ox_schedule
from ox_retrieval import Retrieval, RuntimeFailure
from ox_schedule import Schedule, rules_digest


class FakeApp:
    def __init__(self):
        self.fresh, self.reason, self.failure, self.indexed, self.last_error = True, 'ready', None, 0, None
        self.root = Path('unrelated-vault').absolute()

    @contextmanager
    def state_guard(self):
        yield

    def status(self):
        return {'fresh': self.fresh, 'reason': self.reason, 'indexed_at': 1.0}

    def index(self):
        if self.failure:
            self.last_error = {'code': self.failure, 'operation': 'index'}
            raise RuntimeFailure(self.failure)
        self.indexed += 1
        self.fresh, self.reason = True, 'ready'
        return {'fresh': True, 'indexed_at': 2.0, 'completeness': {'documents': 3}}


class StubJob(Schedule):
    jobs = None

    def register(self):
        self.jobs.add(self.task)

    def unregister(self):
        self.jobs.discard(self.task)

    def registered(self):
        return self.task in self.jobs


class ScheduleCase(unittest.TestCase):
    def setUp(self):
        sandbox = tempfile.TemporaryDirectory()
        self.addCleanup(sandbox.cleanup)
        self.parent = Path(sandbox.name).resolve()
        (self.parent/'vault'/'01_Wiki').mkdir(parents=True)
        self.config = self.parent/'retrieval.config.json'
        self.rules = {'root': 'vault', 'state': 'state', 'allow': ['01_Wiki'], 'exclude': []}
        self.config.write_bytes(json.dumps(self.rules, indent=1).encode())
        self.app = FakeApp()
        patcher = patch.object(ox_schedule, 'Retrieval', lambda **kwargs: self.app)
        patcher.start()
        self.addCleanup(patcher.stop)
        StubJob.jobs = set()
        self.schedule = StubJob(self.config)

    def stale(self):
        self.app.fresh, self.app.reason = False, 'source_changed'

    def outcome(self):
        code, entry = self.schedule.run()
        return code, entry['outcome'], entry.get('reason')

    def test_line_endings_are_the_only_ignored_difference(self):
        self.assertEqual(rules_digest(b'{"a":1,\n"b":2}\n'), rules_digest(b'{"a":1,\r\n"b":2}\r\n'))
        for other in (b'{"a":1,\n"b":2}', b'{"a":1,\n "b":2}\n', b'{"a":1,\r"b":2}\n', b'{"b":2,\n"a":1}\n'):
            self.assertNotEqual(rules_digest(b'{"a":1,\n"b":2}\n'), rules_digest(other))

    def test_not_enabled_changes_nothing(self):
        before = sorted(p.name for p in self.parent.iterdir())
        self.assertEqual(self.schedule.run(), (2, {'outcome': 'not_enabled'}))
        self.assertEqual(self.schedule.status()['automatic_indexing'], 'not_enabled')
        self.assertEqual(sorted(p.name for p in self.parent.iterdir()), before)
        self.assertEqual(self.app.indexed, 0)

    def test_enable_twice_keeps_one_job_and_the_first_baseline(self):
        self.schedule.enable()
        baseline = self.schedule.read('schedule.json')[0]
        self.config.write_bytes(json.dumps(dict(self.rules, exclude=['01_Wiki/private'])).encode())
        status = StubJob(self.config).enable()
        self.assertEqual(len(StubJob.jobs), 1)
        self.assertEqual(self.schedule.read('schedule.json')[0], baseline)
        self.assertEqual(status['automatic_indexing'], 'review_hold')

    def test_changed_file_refreshes_and_success_is_kept_apart_from_later_checks(self):
        self.assertEqual(self.schedule.enable()['automatic_indexing'], 'active')
        self.assertEqual(self.outcome(), (0, 'up_to_date', None))
        self.assertIsNone(self.schedule.status()['last_success'])
        self.stale()
        self.assertEqual(self.outcome(), (0, 'refreshed', 'source_changed'))
        success = self.schedule.status()['last_success']
        self.assertEqual(success['documents'], 3)
        self.schedule.pause()
        self.assertEqual(self.outcome(), (2, 'held', 'manual_pause'))
        status = self.schedule.status()
        self.assertEqual((status['automatic_indexing'], status['last_success']), ('paused', success))
        self.assertEqual(status['last_check']['outcome'], 'held')

    def test_crlf_conversion_of_the_rules_is_not_a_change(self):
        self.schedule.enable()
        raw = self.config.read_bytes()
        self.config.write_bytes(raw.replace(b'\n', b'\r\n'))
        self.assertNotEqual(self.config.read_bytes(), raw)
        self.assertEqual(self.outcome(), (0, 'up_to_date', None))
        self.config.write_bytes(raw)
        self.assertEqual(self.outcome(), (0, 'up_to_date', None))

    def test_rule_change_holds_until_restored_or_approved(self):
        self.schedule.enable()
        approved = self.config.read_bytes()
        self.config.write_bytes(json.dumps(dict(self.rules, exclude=['01_Wiki/private'])).encode())
        self.stale()
        self.assertEqual(self.outcome(), (2, 'held', 'rules_changed'))
        self.assertEqual(self.outcome(), (2, 'held', 'rules_changed'))
        self.assertEqual(self.app.indexed, 0)
        status = self.schedule.status()
        self.assertEqual(status['automatic_indexing'], 'review_hold')
        self.assertEqual(status['hold']['changes'], {'exclude': {'added': ['01_Wiki/private'], 'removed': []}})
        self.assertFalse(self.schedule.resume()['resumed'])
        self.assertEqual(ox_schedule.main(['resume', '--config', str(self.config)]), 2)
        self.assertEqual(self.outcome(), (2, 'held', 'rules_changed'))
        self.config.write_bytes(approved)
        self.assertTrue(self.schedule.resume()['resumed'])
        self.assertEqual(self.outcome(), (0, 'refreshed', 'source_changed'))
        # A deliberate change is adopted only by the explicit approval command.
        self.config.write_bytes(json.dumps(dict(self.rules, allow=['01_Wiki', '03_Operations'])).encode())
        self.assertEqual(self.outcome(), (2, 'held', 'rules_changed'))
        approval = self.schedule.approve_rules()
        self.assertEqual(approval['approved_changes'], {'allow': {'added': ['03_Operations'], 'removed': []}})
        self.assertEqual(approval['automatic_indexing'], 'active')
        self.assertEqual(self.outcome(), (0, 'up_to_date', None))

    def test_unreadable_rules_hold(self):
        self.schedule.enable()
        self.config.unlink()
        self.assertEqual(self.outcome(), (2, 'held', 'rules_changed'))

    def test_manual_pause_survives_checks_and_repeated_setup(self):
        self.schedule.enable()
        self.schedule.pause()
        self.stale()
        self.assertEqual(self.outcome(), (2, 'held', 'manual_pause'))
        self.assertEqual(StubJob(self.config).enable()['automatic_indexing'], 'paused')
        self.assertEqual(self.outcome(), (2, 'held', 'manual_pause'))
        self.assertEqual(self.app.indexed, 0)
        self.assertTrue(self.schedule.resume()['resumed'])
        self.assertEqual(self.outcome(), (0, 'refreshed', 'source_changed'))

    def test_pause_does_not_replace_an_existing_hold(self):
        self.schedule.enable()
        self.schedule.hold('run_failed', 'backend_exit')
        self.schedule.pause()
        self.assertEqual(self.schedule.current_hold()['reason'], 'run_failed')

    def test_failure_holds_and_a_file_saved_mid_refresh_only_skips(self):
        self.schedule.enable()
        self.stale()
        self.app.failure = 'source_changed'
        self.assertEqual(self.outcome(), (2, 'skipped', 'source_changing'))
        self.assertIsNone(self.schedule.current_hold())
        self.app.failure = 'backend_exit'
        self.assertEqual(self.outcome(), (1, 'failed', 'backend_exit'))
        self.app.failure = None
        self.assertEqual(self.outcome(), (2, 'held', 'run_failed'))
        status = self.schedule.status()
        self.assertEqual((status['automatic_indexing'], status['hold']['detail']), ('held', 'backend_exit'))
        self.schedule.resume()
        self.assertEqual(self.outcome(), (0, 'refreshed', 'source_changed'))

    def test_interrupted_run_retries_only_after_a_recorded_restart(self):
        self.schedule.enable()
        self.stale()
        now = ox_schedule.boot_time()
        # Simulated interruption: the run record remains, as after a killed process.
        self.schedule.write('run.json', {'started_at': 1.0, 'boot_time': now, 'pid': 1, 'trigger': 'source_changed'})
        self.assertEqual(self.outcome(), (2, 'held', 'interrupted'))
        self.assertEqual(self.schedule.current_hold()['detail'], 'no_restart_recorded')
        self.assertTrue((self.schedule.dir/'run.json').exists())
        self.assertEqual(self.outcome(), (2, 'held', 'interrupted'))
        self.schedule.resume()
        self.assertEqual(self.outcome(), (0, 'refreshed', 'source_changed'))
        # Simulated restart: the record carries an earlier boot.
        self.stale()
        self.schedule.write('run.json', {'started_at': 1.0, 'boot_time': now - 86400, 'pid': 1, 'trigger': 'source_changed'})
        self.assertEqual(self.outcome(), (0, 'refreshed', 'restart_retry'))
        self.assertFalse((self.schedule.dir/'run.json').exists())
        self.stale()
        (self.schedule.dir/'run.json').write_bytes(b'{')
        self.assertEqual(self.outcome(), (2, 'held', 'interrupted'))
        self.assertEqual(self.schedule.current_hold()['detail'], 'record_unreadable')

    def test_restart_never_clears_a_pause_or_review_hold(self):
        self.schedule.enable()
        self.stale()
        earlier = ox_schedule.boot_time() - 86400
        self.schedule.write('run.json', {'started_at': 1.0, 'boot_time': earlier, 'pid': 1, 'trigger': 'x'})
        for reason in ('manual_pause', 'rules_changed', 'run_failed'):
            self.schedule.remove('hold.json')
            self.schedule.hold(reason)
            self.assertEqual(self.outcome(), (2, 'held', reason))
        self.assertEqual(self.app.indexed, 0)

    def test_damaged_records_hold(self):
        self.schedule.enable()
        (self.schedule.dir/'hold.json').write_bytes(b'[]')
        self.assertEqual(self.outcome(), (2, 'held', 'record_unreadable'))
        self.schedule.remove('hold.json')
        (self.schedule.dir/'schedule.json').write_bytes(b'{')
        self.stale()
        self.assertEqual(self.outcome(), (2, 'held', 'record_unreadable'))
        self.assertEqual(self.app.indexed, 0)

    def test_hold_without_a_reason_still_holds(self):
        self.schedule.enable()
        (self.schedule.dir/'hold.json').write_bytes(b'{}')
        self.stale()
        self.assertEqual(self.outcome(), (2, 'held', 'record_unreadable'))
        self.assertTrue(self.schedule.resume()['resumed'])

    def test_resume_from_a_pause_keeps_a_run_record(self):
        self.schedule.enable()
        self.schedule.pause()
        self.schedule.write('run.json', {'started_at': 1.0, 'boot_time': ox_schedule.boot_time(), 'pid': 1})
        self.schedule.resume()
        self.assertTrue((self.schedule.dir/'run.json').exists())

    def test_planted_or_shared_schedule_folder_is_refused(self):
        other = self.parent/'other.json'
        other.write_bytes(self.config.read_bytes())
        target = self.parent/'elsewhere'
        target.mkdir()
        folder = other.with_name('other.json.schedule')
        try:
            folder.symlink_to(target, target_is_directory=True)
        except OSError:
            self.skipTest('symlink privilege unavailable')
        with self.assertRaises(ValueError):
            StubJob(other)
        self.assertEqual(ox_schedule.main(['uninstall', '--config', str(other)]), 1)
        self.assertEqual(list(target.iterdir()), [])

    @unittest.skipIf(os.name == 'nt', 'POSIX mode check')
    def test_group_readable_schedule_folder_is_refused(self):
        self.schedule.enable()
        self.schedule.dir.chmod(0o750)
        with self.assertRaises(ValueError):
            StubJob(self.config)

    @unittest.skipUnless(os.name == 'nt', 'Windows ACL check')
    def test_broadly_accessible_schedule_folder_is_refused(self):
        folder = self.config.with_name(self.config.name + '.schedule')
        folder.mkdir()  # inherits the temporary folder's ACL instead of the owner-only one
        try:
            StubJob(self.config)
        except ValueError:
            return
        self.skipTest('temporary folder ACL is already owner-only here')

    def test_configuration_inside_the_vault_is_refused(self):
        inside = self.parent/'vault'/'retrieval.config.json'
        inside.write_bytes(json.dumps(dict(self.rules, root='.', state='../state')).encode())
        self.app.root = self.parent/'vault'
        with self.assertRaises(ValueError):
            StubJob(inside).enable()
        self.assertEqual(StubJob.jobs, set())

    def test_uninstall_removes_only_the_job_and_its_records(self):
        self.schedule.enable()
        self.stale()
        self.schedule.run()
        before = self.config.read_bytes()
        note = self.parent/'vault'/'01_Wiki'/'note.md'
        note.write_text('kept', encoding='utf-8')
        status = self.schedule.uninstall()
        self.assertEqual((status['automatic_indexing'], status['job']['registered']), ('not_enabled', False))
        self.assertFalse(self.schedule.dir.exists())
        self.assertEqual((self.config.read_bytes(), note.read_text(encoding='utf-8')), (before, 'kept'))
        self.assertEqual(self.schedule.uninstall()['automatic_indexing'], 'not_enabled')

    def test_commands_other_than_enable_require_enabling(self):
        for command in ('pause', 'resume', 'approve-rules'):
            self.assertEqual(ox_schedule.main([command, '--config', str(self.config)]), 1)
        self.assertFalse(self.schedule.dir.exists())


class WriterLock(unittest.TestCase):
    def test_busy_writer_is_skipped_without_a_hold(self):
        with tempfile.TemporaryDirectory() as sandbox:
            parent = Path(sandbox).resolve()
            (parent/'vault'/'01_Wiki').mkdir(parents=True)
            config = parent/'retrieval.config.json'
            config.write_text(json.dumps({'root': 'vault', 'state': 'state', 'allow': ['01_Wiki'], 'exclude': []}))
            StubJob.jobs = set()
            schedule = StubJob(config)
            schedule.enable()
            holder = Retrieval(parent/'vault', parent/'state', ('01_Wiki',), ())
            with holder.state_guard():  # stands in for a manual index that is still running
                code, entry = schedule.run()
                self.assertEqual((code, entry['outcome'], entry['reason']), (2, 'skipped', 'writer_busy'))
                self.assertEqual(schedule.status()['automatic_indexing'], 'in_progress')
            self.assertIsNone(schedule.current_hold())
            self.assertEqual(schedule.status()['automatic_indexing'], 'active')


class JobDefinition(unittest.TestCase):
    def setUp(self):
        sandbox = tempfile.TemporaryDirectory()
        self.addCleanup(sandbox.cleanup)
        self.config = Path(sandbox.name).resolve()/'runtime & more'/'retrieval.config.json'
        self.config.parent.mkdir()
        self.schedule = Schedule(self.config)
        if os.name == 'nt':
            ox_schedule.state_guard.create_private(self.schedule.dir)
        else:
            self.schedule.dir.mkdir(mode=0o700)
        self.commands = []

    def fake(self, *command):
        self.commands.append(command)
        return type('Done', (), {'returncode': 0})()

    def test_one_job_name_per_configuration(self):
        self.assertEqual(Schedule(self.config).task, self.schedule.task)
        self.assertNotEqual(Schedule(self.config.with_name('other.json')).task, self.schedule.task)
        with self.assertRaises(ValueError):
            Schedule('bad"name.json')

    @unittest.skipUnless(os.name == 'nt', 'Windows task definition')
    def test_windows_task_is_per_user_five_minute_and_single_instance(self):
        with patch.object(Schedule, '_os', self.fake):
            self.schedule.register()
        create = self.commands[-1]
        self.assertEqual(create[1:4], ('/Create', '/TN', self.schedule.task))
        ns = {'t': 'http://schemas.microsoft.com/windows/2004/02/mit/task'}
        task = ET.fromstring((self.schedule.dir/'job.xml').read_bytes().decode('utf-16'))
        self.assertEqual(task.findtext('.//t:Interval', namespaces=ns), 'PT5M')
        self.assertEqual(task.findtext('.//t:MultipleInstancesPolicy', namespaces=ns), 'IgnoreNew')
        self.assertEqual(task.findtext('.//t:LogonType', namespaces=ns), 'InteractiveToken')
        self.assertEqual(task.findtext('.//t:RunLevel', namespaces=ns), 'LeastPrivilege')
        self.assertTrue(task.findtext('.//t:Arguments', namespaces=ns).endswith(f'run --config "{self.config}"'))

    @unittest.skipUnless(sys.platform == 'darwin', 'macOS LaunchAgent definition')
    def test_launch_agent_is_a_user_agent_with_a_five_minute_interval(self):
        import plistlib
        with tempfile.TemporaryDirectory() as home:
            self.schedule.plist = Path(home)/f'{self.schedule.label}.plist'
            with patch.object(Schedule, '_os', self.fake):
                self.schedule.register()
            job = plistlib.loads(self.schedule.plist.read_bytes())
        self.assertEqual((job['Label'], job['StartInterval']), (self.schedule.label, 300))
        self.assertEqual(job['ProgramArguments'][-3:], ['run', '--config', str(self.config)])
        self.assertTrue(all(command[2].startswith('gui/') for command in self.commands))


if __name__ == '__main__':
    unittest.main()

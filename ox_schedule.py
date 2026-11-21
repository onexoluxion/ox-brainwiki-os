"""Opt-in automatic indexing: one per-user OS job that checks every five minutes.

The job runs `run`, which refreshes the index through the same Retrieval.index()
and state lock as the manual `ox_retrieval.py index` command. Records live in a
private folder beside the configuration file and hold codes, times and the
approved indexing rules only, never note content.
"""
import argparse
from contextlib import ExitStack
import hashlib
import json
import os
from pathlib import Path
import plistlib
import subprocess
import sys
import tempfile
import time
from xml.sax.saxutils import escape

from ox_retrieval import BASE, Retrieval, RuntimeFailure, parse_config

INTERVAL_SECONDS = 300
SCHEMA = 1
MAX_RECORD_BYTES = 65536
MAX_CONFIG_BYTES = 16384
HISTORY_LINES = 200
BOOT_TOLERANCE = 120  # seconds; boot time is derived from uptime and can drift slightly
RECORDS = ('schedule.json', 'hold.json', 'run.json', 'last.json', 'success.json',
           'history.jsonl', 'job.xml')
TRANSIENT = (OSError,)
if os.name == 'nt':
    import ctypes
    import pywintypes
    import state_guard
    TRANSIENT = (OSError, pywintypes.error)

RESOLVE = {
    'manual_pause': 'Run `ox_schedule.py resume` when automatic indexing should continue.',
    'rules_changed': ('The indexing rules differ from the approved baseline. Restore the approved '
                      'configuration and run `resume`, or review the listed changes and run '
                      '`approve-rules` to accept them.'),
    'interrupted': ('A refresh stopped without a result and no restart explains it. Run '
                    '`ox_retrieval.py status`, then `ox_schedule.py resume` to let the next check rebuild.'),
    'run_failed': ('The last refresh failed. Run `ox_retrieval.py index` manually to see the error, '
                   'fix the cause, then run `ox_schedule.py resume`.'),
    'record_unreadable': ('A schedule record could not be read. Inspect the schedule folder, then run '
                          '`ox_schedule.py resume`; if `schedule.json` itself is damaged, run `uninstall` '
                          'and `enable` again after reviewing the configuration.'),
}


def rules_digest(raw):
    """LF and CRLF are interchangeable at line boundaries; every other byte is significant."""
    return hashlib.sha256(raw.replace(b'\r\n', b'\n')).hexdigest()


def boot_time():
    """Approximate time of the current boot; a different value means the machine restarted."""
    if os.name == 'nt':
        ticks = ctypes.WinDLL('kernel32').GetTickCount64
        ticks.restype = ctypes.c_uint64
        return time.time() - ticks() / 1000
    out = subprocess.run(['/usr/sbin/sysctl', '-n', 'kern.boottime'], capture_output=True,
                         text=True, timeout=10, check=True).stdout
    return float(out.split('sec =')[1].split(',')[0])


class Schedule:
    def __init__(self, config):
        self.config = Path(os.path.abspath(config))  # one spelling, so one job, per configuration
        if any(c in str(self.config) for c in '"<>|%\r\n\0') or '$(' in str(self.config):
            raise ValueError('configuration path contains unsupported characters')
        self.dir = self.config.with_name(self.config.name + '.schedule')
        self.check_folder()
        key = str(self.config).casefold() if os.name == 'nt' else str(self.config)
        self.id = hashlib.sha256(key.encode('utf-8')).hexdigest()[:10]
        self.task = f'OX BrainWiki Index {self.id}'
        self.label = f'com.onexoluxion.brainwiki.index.{self.id}'
        self.plist = Path.home()/'Library'/'LaunchAgents'/f'{self.label}.plist'

    # --- records -----------------------------------------------------------
    def check_folder(self):
        """An existing records folder must be a real, owner-only directory: it holds the approved baseline."""
        if not os.path.lexists(self.dir):
            return
        if self.dir.is_symlink() or self.dir.is_junction() or not self.dir.is_dir():
            raise ValueError('schedule folder must be an ordinary directory')
        if os.name == 'nt':
            state_guard.validate_acl(self.dir)
        else:
            info = self.dir.stat()
            if info.st_uid != os.geteuid() or info.st_mode & 0o077:
                raise ValueError('schedule folder must be private to its owner')

    def read(self, name):
        """Return (data, state): state is 'missing', 'ok' or 'unreadable'."""
        try:
            with (self.dir/name).open('rb') as stream:
                raw = stream.read(MAX_RECORD_BYTES + 1)
            data = json.loads(raw) if len(raw) <= MAX_RECORD_BYTES else None
            return (data, 'ok') if isinstance(data, dict) else (None, 'unreadable')
        except FileNotFoundError:
            return None, 'missing'
        except (OSError, ValueError, RecursionError):
            return None, 'unreadable'

    def write(self, name, data):
        with tempfile.NamedTemporaryFile(mode='wb', dir=self.dir, prefix='record-',
                                         suffix='.tmp', delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(json.dumps(data, allow_nan=False).encode('utf-8'))
            stream.flush()
            os.fsync(stream.fileno())
        try:
            os.replace(temporary, self.dir/name)
        finally:
            temporary.unlink(missing_ok=True)

    def remove(self, name):
        (self.dir/name).unlink(missing_ok=True)

    def record(self, outcome, reason=None, **extra):
        entry = {'outcome': outcome, 'reason': reason, 'at': time.time(), **extra}
        self.write('last.json', entry)
        history = self.dir/'history.jsonl'
        try:
            lines = history.read_text(encoding='utf-8').splitlines()[-(HISTORY_LINES - 1):]
        except (OSError, ValueError):
            lines = []
        history.write_text('\n'.join([*lines, json.dumps(entry)]) + '\n', encoding='utf-8')
        return entry

    def hold(self, reason, detail=None, **extra):
        current, state = self.read('hold.json')
        if state == 'missing':  # the first hold is the one the operator must see
            self.write('hold.json', {'reason': reason, 'detail': detail, 'since': time.time(), **extra})

    def current_hold(self):
        hold, state = self.read('hold.json')
        if state == 'unreadable' or (hold is not None and not isinstance(hold.get('reason'), str)):
            return {'reason': 'record_unreadable', 'detail': 'hold.json', 'since': None}
        return hold

    # --- indexing rules ----------------------------------------------------
    def read_rules(self):
        """Return (raw bytes or None, parsed rule summary or None)."""
        try:
            with self.config.open('rb') as stream:
                raw = stream.read(MAX_CONFIG_BYTES + 1)
        except OSError:
            return None, None
        try:
            parsed = parse_config(raw, self.config)
            summary = {'root': str(parsed['root']), 'state': str(parsed['state']),
                       'allow': list(parsed['allowed']), 'exclude': list(parsed['excluded'])}
        except (ValueError, TypeError, RecursionError):
            summary = None
        return raw, summary

    def rule_changes(self, approved, current):
        if current is None:
            return {'configuration': 'unreadable or invalid'}
        changes = {}
        for key in ('root', 'state'):
            if approved.get(key) != current[key]:
                changes[key] = {'approved': approved.get(key), 'current': current[key]}
        for key in ('allow', 'exclude'):
            before, after = approved.get(key, []), current[key]
            added = [p for p in after if p not in before]
            removed = [p for p in before if p not in after]
            if added or removed or before != after:
                changes[key] = {'added': added, 'removed': removed}
        return changes or {'formatting': 'bytes differ from the approved file; the parsed rules are the same'}

    # --- operating-system job ---------------------------------------------
    def interpreter(self):
        if os.name == 'nt':
            windowless = Path(sys.executable).with_name('pythonw.exe')
            return windowless if windowless.is_file() else Path(sys.executable)
        return Path(sys.executable)

    def _os(self, *command):
        return subprocess.run(list(command), capture_output=True, timeout=60)

    def _schtasks(self):
        return str(Path(os.environ.get('SystemRoot', r'C:\Windows'))/'System32'/'schtasks.exe')

    def _domain(self):
        return f'gui/{os.getuid()}'

    def register(self):
        """Create or replace the single job for this configuration."""
        script = BASE/'ox_schedule.py'
        if os.name == 'nt':
            sid = state_guard.win32security.ConvertSidToStringSid(state_guard.SID)
            start = time.strftime('%Y-%m-%dT%H:%M:%S', time.localtime(time.time() + 60))
            xml = f'''<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo><Description>OX BrainWiki OS automatic indexing. Checks every five minutes while you are signed in.</Description></RegistrationInfo>
  <Triggers><TimeTrigger><Repetition><Interval>PT{INTERVAL_SECONDS // 60}M</Interval><StopAtDurationEnd>false</StopAtDurationEnd></Repetition><StartBoundary>{start}</StartBoundary><Enabled>true</Enabled></TimeTrigger></Triggers>
  <Principals><Principal id="Author"><UserId>{escape(sid)}</UserId><LogonType>InteractiveToken</LogonType><RunLevel>LeastPrivilege</RunLevel></Principal></Principals>
  <Settings><MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy><DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries><StopIfGoingOnBatteries>false</StopIfGoingOnBatteries><StartWhenAvailable>true</StartWhenAvailable><ExecutionTimeLimit>PT1H</ExecutionTimeLimit><Enabled>true</Enabled></Settings>
  <Actions Context="Author"><Exec><Command>{escape(str(self.interpreter()))}</Command><Arguments>{escape(f'"{script}" run --config "{self.config}"')}</Arguments><WorkingDirectory>{escape(str(BASE))}</WorkingDirectory></Exec></Actions>
</Task>'''
            definition = self.dir/'job.xml'
            definition.write_text(xml, encoding='utf-16')
            done = self._os(self._schtasks(), '/Create', '/TN', self.task, '/XML', str(definition), '/F')
            if done.returncode:
                raise RuntimeError('the scheduled task could not be registered')
            return
        job = {'Label': self.label, 'StartInterval': INTERVAL_SECONDS, 'RunAtLoad': True,
               'ProcessType': 'Background', 'WorkingDirectory': str(BASE),
               'ProgramArguments': [str(self.interpreter()), str(script), 'run', '--config', str(self.config)],
               'StandardOutPath': '/dev/null', 'StandardErrorPath': '/dev/null'}
        self.plist.parent.mkdir(parents=True, exist_ok=True)
        self._os('/bin/launchctl', 'bootout', f'{self._domain()}/{self.label}')
        self.plist.write_bytes(plistlib.dumps(job))
        for _ in range(10):  # bootout is asynchronous; bootstrap succeeds once the old job is gone
            if self._os('/bin/launchctl', 'bootstrap', self._domain(), str(self.plist)).returncode == 0:
                return
            if self.registered():
                return
            time.sleep(0.5)
        raise RuntimeError('the LaunchAgent could not be loaded')

    def unregister(self):
        if os.name == 'nt':
            if self.registered():
                if self._os(self._schtasks(), '/Delete', '/TN', self.task, '/F').returncode:
                    raise RuntimeError('the scheduled task could not be removed')
            return
        self._os('/bin/launchctl', 'bootout', f'{self._domain()}/{self.label}')
        for _ in range(20):
            if not self._loaded():
                break
            time.sleep(0.25)
        self.plist.unlink(missing_ok=True)

    def _loaded(self):
        return self._os('/bin/launchctl', 'print', f'{self._domain()}/{self.label}').returncode == 0

    def registered(self):
        if os.name == 'nt':
            return self._os(self._schtasks(), '/Query', '/TN', self.task).returncode == 0
        return self.plist.is_file() and self._loaded()

    def start_now(self):
        """Ask the operating system to start the registered job once (used by acceptance checks)."""
        if os.name == 'nt':
            return self._os(self._schtasks(), '/Run', '/TN', self.task).returncode == 0
        return self._os('/bin/launchctl', 'kickstart', f'{self._domain()}/{self.label}').returncode == 0

    # --- commands ----------------------------------------------------------
    def enable(self):
        raw, summary = self.read_rules()
        if raw is None or summary is None:
            raise ValueError('configuration is unreadable or invalid')
        app = Retrieval(**parse_config(raw, self.config))  # the same validation the indexer applies
        if self.dir.is_relative_to(app.root):
            raise ValueError('keep the configuration outside the vault')
        if not self.dir.exists():
            if os.name == 'nt':
                state_guard.create_private(self.dir)
            else:
                os.mkdir(self.dir, 0o700)
        self.register()  # before the baseline, so a failed registration leaves nothing approved
        existing, state = self.read('schedule.json')
        if state == 'missing':
            # Enabling is the operator's approval of the rules as they are now.
            self.write('schedule.json', {'schema': SCHEMA, 'rules_sha256': rules_digest(raw),
                                         'rules': summary, 'enabled_at': time.time()})
        elif state == 'unreadable':
            self.hold('record_unreadable', 'schedule.json')
        return self.status()

    def pause(self):
        self._require_enabled()
        self.hold('manual_pause')
        return self.status()

    def resume(self):
        schedule = self._require_enabled()
        hold = self.current_hold()
        if hold and hold['reason'] == 'rules_changed':
            raw, _ = self.read_rules()
            if raw is None or rules_digest(raw) != schedule['rules_sha256']:
                return dict(self.status(), resumed=False)
        self.remove('hold.json')
        if hold and hold['reason'] == 'interrupted':
            self.remove('run.json')  # the operator has reviewed the interrupted run
        return dict(self.status(), resumed=True)

    def approve_rules(self):
        schedule = self._require_enabled()
        raw, summary = self.read_rules()
        if raw is None or summary is None:
            raise ValueError('configuration is unreadable or invalid')
        changes = None if rules_digest(raw) == schedule['rules_sha256'] else self.rule_changes(schedule['rules'], summary)
        self.write('schedule.json', dict(schedule, rules_sha256=rules_digest(raw), rules=summary,
                                         approved_at=time.time()))
        hold = self.current_hold()
        if hold and hold['reason'] == 'rules_changed':
            self.remove('hold.json')
        return dict(self.status(), approved_changes=changes)

    def uninstall(self):
        """Remove the job and its records. The vault, configuration and index are not touched."""
        self.unregister()
        if self.dir.is_dir():  # check_folder() already refused links and junctions
            for name in RECORDS:
                self.remove(name)
            try:
                self.dir.rmdir()
            except OSError:
                pass  # unexpected extra files stay for the operator to inspect
        return self.status()

    def _require_enabled(self):
        schedule, state = self.read('schedule.json')
        if state != 'ok' or not isinstance(schedule.get('rules_sha256'), str) or not isinstance(schedule.get('rules'), dict):
            raise ValueError('automatic indexing is not enabled for this configuration')
        return schedule

    def status(self):
        schedule, state = self.read('schedule.json')
        registered = self.registered()
        result = {'automatic_indexing': 'not_enabled',
                  'job': {'name': self.task if os.name == 'nt' else self.label, 'registered': registered,
                          'check_interval_seconds': INTERVAL_SECONDS},
                  'hold': None, 'last_check': self.read('last.json')[0],
                  'last_success': self.read('success.json')[0], 'index': None}
        if state == 'missing':
            return result
        hold = self.current_hold()
        raw, summary = self.read_rules()
        if state == 'unreadable':
            hold = hold or {'reason': 'record_unreadable', 'detail': 'schedule.json', 'since': None}
        elif not hold and (raw is None or rules_digest(raw) != schedule.get('rules_sha256')):
            hold = {'reason': 'rules_changed', 'detail': 'detected by status; the next check records it', 'since': None}
        if hold:
            hold = dict(hold, resolve=RESOLVE.get(hold['reason'], RESOLVE['record_unreadable']))
            if hold['reason'] == 'rules_changed' and state == 'ok':
                hold['changes'] = self.rule_changes(schedule.get('rules', {}), summary)
        result['hold'] = hold
        busy = False
        if raw is not None:
            try:
                app = Retrieval(**parse_config(raw, self.config))
                with ExitStack() as stack:
                    try:
                        stack.enter_context(app.state_guard())
                    except TRANSIENT:
                        busy = True
                    else:
                        index = app.status()
                        result['index'] = {k: index[k] for k in ('fresh', 'reason', 'indexed_at')}
            except Exception:
                result['index'] = {'fresh': False, 'reason': 'source_or_state_unavailable', 'indexed_at': None}
        if busy:
            result['automatic_indexing'] = 'in_progress'
        elif hold:
            result['automatic_indexing'] = {'manual_pause': 'paused', 'rules_changed': 'review_hold'}.get(hold['reason'], 'held')
        elif not registered:
            result['automatic_indexing'] = 'job_missing'
        else:
            result['automatic_indexing'] = 'active'
        return result

    def run(self):
        """One scheduled check. Returns (exit code, recorded entry)."""
        schedule, state = self.read('schedule.json')
        if state == 'missing':
            return 2, {'outcome': 'not_enabled'}
        if state == 'unreadable' or not isinstance(schedule.get('rules_sha256'), str):
            schedule = {'rules_sha256': None}
            self.hold('record_unreadable', 'schedule.json')
        hold = self.current_hold()
        if hold:
            return 2, self.record('held', hold['reason'])
        raw, _ = self.read_rules()
        if raw is None or rules_digest(raw) != schedule['rules_sha256']:
            self.hold('rules_changed')
            return 2, self.record('held', 'rules_changed')
        try:
            app = Retrieval(**parse_config(raw, self.config))
        except OSError:
            return 2, self.record('skipped', 'source_unavailable')
        except Exception:
            self.hold('run_failed', 'configuration_rejected')
            return 1, self.record('failed', 'configuration_rejected')
        with ExitStack() as stack:
            try:
                stack.enter_context(app.state_guard())
            except TRANSIENT:
                # Another index, status or search holds the single-writer lock.
                return 2, self.record('skipped', 'writer_busy')
            except Exception:
                self.hold('run_failed', 'state_rejected')
                return 1, self.record('failed', 'state_rejected')
            previous, run_state = self.read('run.json')
            retry = False
            if run_state != 'missing':
                started = previous.get('boot_time') if previous else None
                if type(started) in (int, float) and abs(boot_time() - started) > BOOT_TOLERANCE:
                    retry = True  # the recorded run began before a restart: rebuilding is safe
                else:
                    detail = 'no_restart_recorded' if type(started) in (int, float) else 'record_unreadable'
                    self.hold('interrupted', detail)
                    return 2, self.record('held', 'interrupted')
            index = app.status()
            if index['fresh']:
                self.remove('run.json')
                return 0, self.record('up_to_date')
            if index['reason'] == 'source_or_state_unavailable':
                return 2, self.record('skipped', 'source_unavailable')
            trigger = 'restart_retry' if retry else index['reason']
            started = time.time()
            self.write('run.json', {'started_at': started, 'boot_time': boot_time(), 'pid': os.getpid(),
                                    'trigger': trigger})
            try:
                done = app.index()
            except RuntimeFailure:
                code = app.last_error['code']
            except (ValueError, TypeError):
                code = 'invalid_request'
            except Exception:
                code = 'state_unavailable'
            else:
                self.remove('run.json')
                finished = time.time()
                self.write('success.json', {'at': finished, 'indexed_at': done['indexed_at'], 'trigger': trigger,
                                            'documents': done['completeness'].get('documents'),
                                            'seconds': round(finished - started, 1)})
                return 0, self.record('refreshed', trigger, seconds=round(finished - started, 1))
            self.remove('run.json')
            if code == 'source_changed':  # a file was saved during the refresh; the next check retries
                return 2, self.record('skipped', 'source_changing')
            self.hold('run_failed', code)
            return 1, self.record('failed', code)


def main(argv=None):
    parser = argparse.ArgumentParser(description='Opt-in automatic indexing for one retrieval configuration.')
    parser.add_argument('command', choices=['enable', 'status', 'pause', 'resume', 'approve-rules', 'uninstall', 'run'])
    parser.add_argument('--config', required=True, help='the retrieval configuration used for manual indexing')
    args = parser.parse_args(argv)
    code = 0
    try:
        schedule = Schedule(args.config)
        if args.command == 'run':
            code, result = schedule.run()
        else:
            result = getattr(schedule, args.command.replace('-', '_'))()
            if result.get('resumed') is False:
                code = 2
    except (ValueError, RuntimeError) as error:
        result, code = {'error': str(error)}, 1
    except Exception:
        result, code = {'error': 'state_unavailable'}, 1
    if sys.stdout is not None:  # the Windows job runs without a console
        print(json.dumps(result, indent=2))
    return code


if __name__ == '__main__':
    raise SystemExit(main())

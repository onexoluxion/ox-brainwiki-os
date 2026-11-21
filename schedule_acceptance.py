"""Automatic-indexing acceptance: real backend, real per-user OS job, disposable invented vault.

Registers a test job for a temporary configuration, exercises it and removes it.
Restart recovery is simulated (a killed process plus an edited boot record); no
machine restart is performed. `--natural` waits for the scheduler's own
five-minute trigger instead of asking the OS to start the job on demand.
"""
import argparse
import asyncio
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tempfile
import time

from fastmcp import Client
from fastmcp.client.transports import StdioTransport
from ox_retrieval import BASE, Retrieval, load_config
from ox_schedule import Schedule, TRANSIENT
from runtime_acceptance import payload, reuse_models

NOTE = '01_Wiki/suppliers/harbor-ceramics.md'
DRAFT = '00_Raw/_proposals/harbor-ceramics-draft.md'
DRAFT_DATE = '2031-04-02'
QUESTION = 'When will Harbor Ceramics deliver the glazed tile order?'


class Bench:
    def __init__(self, natural):
        self.natural = natural
        self.parent = Path(tempfile.mkdtemp(prefix='ox-sched-')).resolve()
        self.vault, self.runtime = self.parent/'vault', self.parent/'runtime'
        (self.vault/NOTE).parent.mkdir(parents=True)
        (self.vault/DRAFT).parent.mkdir(parents=True)
        self.runtime.mkdir()
        self.set_date('2031-03-14')
        (self.vault/'01_Wiki'/'index.md').write_text('# Wiki index\n- [Harbor Ceramics](suppliers/harbor-ceramics.md)\n', encoding='utf-8')
        (self.vault/DRAFT).write_text(
            f'# Unreviewed draft\nHarbor Ceramics might move the glazed tile delivery to {DRAFT_DATE}.\n', encoding='utf-8')
        self.config = self.runtime/'retrieval.config.json'
        self.rules = {'root': str(self.vault), 'state': str(self.runtime/'state'), 'allow': ['01_Wiki'], 'exclude': []}
        self.write_rules(self.rules)
        self.app = Retrieval(**load_config(self.config))
        reuse_models(self.app)
        self.schedule = Schedule(self.config)

    def set_date(self, date):
        (self.vault/NOTE).write_text(
            f'# Supplier: Harbor Ceramics\nPurchase order HC-7731, glazed tile.\nConfirmed delivery date: {date}.\n',
            encoding='utf-8')

    def write_rules(self, rules, newline='\n'):
        self.config.write_bytes(json.dumps(rules, indent=1).replace('\n', newline).encode('utf-8'))

    def cli(self, script, command):
        done = subprocess.run([sys.executable, str(BASE/script), command, '--config', str(self.config)],
                              capture_output=True, text=True, timeout=900)
        try:
            return done.returncode, json.loads(done.stdout)
        except ValueError:
            return done.returncode, {}

    def tree(self):
        return {p.relative_to(self.parent).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in [*self.vault.rglob('*'), self.config] if p.is_file()}

    def jobs(self):
        if os.name == 'nt':
            listing = subprocess.run([self.schedule._schtasks(), '/Query', '/FO', 'CSV', '/NH'],
                                     capture_output=True, text=True, timeout=60).stdout
            return sum(self.schedule.task in line for line in listing.splitlines())
        return len(list(self.schedule.plist.parent.glob(f'{self.schedule.label}*'))) if self.schedule.registered() else 0

    def history(self):
        try:
            lines = (self.schedule.dir/'history.jsonl').read_text(encoding='utf-8').splitlines()
            return [json.loads(line) for line in lines]
        except (OSError, ValueError):
            return []

    def scheduled(self, outcome, reason=None, natural=False, timeout=240):
        """Let the registered OS job run and return the check it recorded."""
        since = time.time()
        deadline = since + (420 if natural else timeout)
        nudged = 0
        self.starts = []  # whether each on-demand start was accepted, for the failure report
        while time.time() < deadline:
            if not natural and time.time() - nudged > 30:
                self.starts.append(self.schedule.start_now())
                nudged = time.time()
            for entry in self.history():
                if entry['at'] > since and entry['outcome'] == outcome and (reason is None or entry['reason'] == reason):
                    return entry
            time.sleep(1)
        raise AssertionError(f'no scheduled {outcome}/{reason} check; saw {self.history()[-3:]}')

    def diagnostics(self):
        """State that explains a failed wait: was a refresh running, was the job loaded, did it start?"""
        report = {'on_demand_starts_accepted': getattr(self, 'starts', None)}
        for name in ('run.json', 'hold.json', 'last.json'):
            report[name] = self.schedule.read(name)[0]
        try:
            with self.app.state_guard():
                report['writer_lock'] = 'free'
        except TRANSIENT:
            report['writer_lock'] = 'held'
        except Exception as error:
            report['writer_lock'] = type(error).__name__
        try:
            status = self.schedule.status()
            report['status'] = {key: status[key] for key in ('automatic_indexing', 'job', 'index')}
        except Exception as error:
            report['status'] = type(error).__name__
        if os.name == 'nt':
            command = [self.schedule._schtasks(), '/Query', '/TN', self.schedule.task, '/V', '/FO', 'LIST']
            wanted = ('Status:', 'Last Run Time:', 'Last Result:', 'Next Run Time:')
        else:
            command = ['/bin/launchctl', 'print', f'{self.schedule._domain()}/{self.schedule.label}']
            wanted = ('state =', 'runs =', 'last exit code', 'pid =', 'run interval', 'last terminating signal')
        try:
            done = subprocess.run(command, capture_output=True, text=True, timeout=60)
            report['os_job'] = {'exit': done.returncode,
                                'lines': [line.strip() for line in done.stdout.splitlines()
                                          if any(word in line for word in wanted)][:12]}
        except Exception as error:
            report['os_job'] = type(error).__name__
        return report

    def writer_free(self, timeout=330):
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                with self.app.state_guard():
                    return
            except TRANSIENT:
                time.sleep(0.5)
        raise AssertionError('writer lock was not released')

    def writer_held(self, timeout=60):
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                with self.app.state_guard():
                    pass
            except TRANSIENT:
                return
            time.sleep(0.05)
        raise AssertionError('writer lock was never taken')

    async def _query(self, calls):
        transport = StdioTransport(command=sys.executable,
                                   args=[str(BASE/'ox_retrieval.py'), 'serve', '--config', str(self.config)])
        results = []
        async with Client(transport) as client:
            assert {t.name for t in await client.list_tools()} == {'search', 'read', 'list', 'status'}
            for name, arguments in calls:
                try:
                    results.append(payload(await client.call_tool(name, arguments)))
                except Exception as error:
                    results.append({'error': str(error)})
        return results

    def mcp(self, *calls):
        return asyncio.run(self._query(calls))

    def retrieved(self, date):
        """The read-only connector returns the reviewed file with this date and nothing from the draft."""
        semantic, exact, draft, read = self.mcp(
            ('search', {'query': QUESTION, 'mode': 'semantic', 'scope': '01_Wiki'}),
            ('search', {'query': date, 'mode': 'exact', 'scope': '01_Wiki'}),
            ('search', {'query': DRAFT_DATE, 'mode': 'exact', 'scope': '01_Wiki'}),
            ('read', {'path': DRAFT}))
        assert semantic['results'][0]['path'] == NOTE and date in semantic['results'][0]['excerpt'], semantic
        assert [r['path'] for r in exact['results']] == [NOTE], exact
        assert draft['results'] == [] and 'error' in read, (draft, read)
        assert all(DRAFT_DATE not in r['excerpt'] for r in semantic['results'])


def upgrade(b):
    """An existing manual installation is untouched until the operator opts in."""
    assert b.cli('ox_retrieval.py', 'index')[0] == 0
    before = b.tree()
    code, status = b.cli('ox_schedule.py', 'status')
    assert (code, status['automatic_indexing'], status['job']['registered']) == (0, 'not_enabled', False)
    assert b.cli('ox_schedule.py', 'run') == (2, {'outcome': 'not_enabled'})
    assert not b.schedule.dir.exists() and b.jobs() == 0 and b.tree() == before
    b.set_date('2031-03-15')
    assert b.cli('ox_retrieval.py', 'status')[1]['fresh'] is False  # nothing refreshed it automatically
    assert b.cli('ox_retrieval.py', 'index')[0] == 0 and b.cli('ox_retrieval.py', 'status')[1]['fresh'] is True
    b.set_date('2031-03-14')
    assert b.cli('ox_retrieval.py', 'index')[0] == 0


def repeated_setup(b):
    for _ in range(2):
        code, status = b.cli('ox_schedule.py', 'enable')
        assert code == 0 and status['job']['registered'] and status['automatic_indexing'] in ('active', 'in_progress'), status
    assert b.jobs() == 1


def seller_example(b):
    b.retrieved('2031-03-14')
    b.set_date('2031-03-21')
    started = time.time()
    entry = b.scheduled('refreshed', natural=b.natural)
    code, status = b.cli('ox_schedule.py', 'status')
    assert status['automatic_indexing'] == 'active' and status['index']['fresh'], status
    assert status['last_success']['at'] >= started and status['last_success']['documents'] == 2
    b.retrieved('2031-03-21')
    return {'trigger': 'scheduler interval' if b.natural else 'OS on-demand start of the registered job',
            'seconds_from_edit_to_refresh': round(entry['at'] - started, 1)}


def overlap(b):
    b.set_date('2031-03-22')
    with b.app.state_guard():  # a manual operation holds the single-writer lock
        b.scheduled('skipped', 'writer_busy')
        assert b.cli('ox_schedule.py', 'status')[1]['automatic_indexing'] == 'in_progress'
    b.writer_free()
    manual = subprocess.Popen([sys.executable, str(BASE/'ox_retrieval.py'), 'index', '--config', str(b.config)],
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    b.writer_held()
    code, entry = b.cli('ox_schedule.py', 'run')
    assert manual.wait(timeout=600) == 0 and (code, entry['outcome'], entry['reason']) == (2, 'skipped', 'writer_busy')
    status = b.cli('ox_schedule.py', 'status')[1]
    assert status['hold'] is None and status['index']['fresh'] and status['last_check']['outcome'] == 'skipped'
    assert status['last_success']['at'] < status['last_check']['at']
    b.retrieved('2031-03-22')


def line_endings(b):
    b.write_rules(b.rules, '\r\n')
    assert b'\r\n' in b.config.read_bytes()
    b.scheduled('up_to_date')
    b.write_rules(b.rules)
    b.scheduled('up_to_date')
    assert b.cli('ox_schedule.py', 'status')[1]['hold'] is None


def exclusion_change(b):
    b.write_rules(dict(b.rules, exclude=['01_Wiki/suppliers']))
    b.set_date('2031-03-23')
    b.scheduled('held', 'rules_changed')
    status = b.cli('ox_schedule.py', 'status')[1]
    assert status['automatic_indexing'] == 'review_hold', status
    assert status['hold']['changes'] == {'exclude': {'added': ['01_Wiki/suppliers'], 'removed': []}}
    assert b.cli('ox_schedule.py', 'resume')[0] == 2  # a changed baseline is never adopted by resume
    b.scheduled('held', 'rules_changed')
    b.write_rules(b.rules)  # the operator restores the approved rules
    assert b.cli('ox_schedule.py', 'resume')[1]['resumed'] is True
    b.scheduled('refreshed')
    b.retrieved('2031-03-23')
    b.write_rules(dict(b.rules, exclude=['01_Wiki/suppliers']))  # or approves a deliberate change
    b.scheduled('held', 'rules_changed')
    code, approval = b.cli('ox_schedule.py', 'approve-rules')
    assert code == 0 and approval['approved_changes']['exclude']['added'] == ['01_Wiki/suppliers']
    b.scheduled('refreshed')
    hidden, = b.mcp(('search', {'query': '2031-03-23', 'mode': 'exact', 'scope': '01_Wiki'}))
    assert hidden['results'] == [], hidden
    b.write_rules(b.rules)
    assert b.cli('ox_schedule.py', 'approve-rules')[0] == 0
    b.scheduled('refreshed')


def killed_run(b, date):
    b.set_date(date)
    run = subprocess.Popen([sys.executable, str(BASE/'ox_schedule.py'), 'run', '--config', str(b.config)],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    deadline = time.time() + 120
    while not (b.schedule.dir/'run.json').exists():
        assert run.poll() is None and time.time() < deadline, 'the run ended before it could be interrupted'
        time.sleep(0.05)
    run.kill()
    run.wait(timeout=30)
    b.writer_free()
    assert (b.schedule.dir/'run.json').exists()


def restart_recovery(b):
    killed_run(b, '2031-03-24')  # a process killed in this boot is ambiguous: hold
    b.scheduled('held', 'interrupted')
    status = b.cli('ox_schedule.py', 'status')[1]
    assert (status['automatic_indexing'], status['hold']['detail']) == ('held', 'no_restart_recorded')
    assert b.cli('ox_schedule.py', 'resume')[1]['resumed'] is True
    b.scheduled('refreshed')
    killed_run(b, '2031-03-25')
    record = json.loads((b.schedule.dir/'run.json').read_text())
    b.schedule.write('run.json', dict(record, boot_time=record['boot_time'] - 86400))  # simulated restart
    assert b.scheduled('refreshed', 'restart_retry')
    assert b.cli('ox_schedule.py', 'status')[1]['hold'] is None
    b.retrieved('2031-03-25')


def manual_pause(b):
    assert b.cli('ox_schedule.py', 'pause')[1]['automatic_indexing'] == 'paused'
    b.set_date('2031-03-26')
    b.scheduled('held', 'manual_pause')
    earlier = json.loads((b.schedule.dir/'hold.json').read_text())['since']
    # Simulated restart: a leftover run record from an earlier boot must not lift the pause.
    b.schedule.write('run.json', {'started_at': 1.0, 'boot_time': time.time() - 10 * 86400, 'pid': 1, 'trigger': 'x'})
    assert b.cli('ox_schedule.py', 'enable')[1]['automatic_indexing'] == 'paused' and b.jobs() == 1
    b.scheduled('held', 'manual_pause')
    assert json.loads((b.schedule.dir/'hold.json').read_text())['since'] == earlier
    assert b.cli('ox_retrieval.py', 'status')[1]['fresh'] is False
    assert b.cli('ox_schedule.py', 'resume')[1]['resumed'] is True
    b.scheduled('refreshed')
    b.retrieved('2031-03-26')


def uninstall(b):
    before = b.tree()
    code, status = b.cli('ox_schedule.py', 'uninstall')
    assert (code, status['automatic_indexing'], status['job']['registered']) == (0, 'not_enabled', False), status
    assert b.jobs() == 0 and not b.schedule.dir.exists() and b.tree() == before
    assert b.cli('ox_retrieval.py', 'status')[1]['fresh'] is True  # the index is preserved
    b.set_date('2031-03-27')
    assert b.cli('ox_retrieval.py', 'index')[0] == 0  # the manual workflow still works
    b.retrieved('2031-03-27')


CHECKS = [('upgrade_keeps_manual_install', upgrade, 'native'),
          ('repeated_setup_one_job', repeated_setup, 'native'),
          ('seller_delivery_date_refresh_and_draft_excluded', seller_example, 'native'),
          ('overlapping_manual_and_scheduled', overlap, 'native'),
          ('rule_file_lf_crlf', line_endings, 'native'),
          ('substantive_exclusion_change_holds', exclusion_change, 'native'),
          ('restart_recovery', restart_recovery, 'simulated interruption (killed process, edited boot record)'),
          ('persistent_manual_pause', manual_pause, 'native job; restart simulated'),
          ('uninstall_preserves_vault_settings_index', uninstall, 'native')]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--natural', action='store_true', help="wait for the scheduler's own interval in the seller example")
    parser.add_argument('--seller-only', action='store_true',
                        help='stop after the seller example and keep the workspace and job for client checks')
    args = parser.parse_args()
    started = time.monotonic()
    bench = Bench(args.natural)
    report = {'platform': f'{platform.system()} {platform.release()} {platform.machine()}',
              'scheduler': 'Windows Scheduled Task' if os.name == 'nt' else 'macOS LaunchAgent', 'checks': {}}
    try:
        for name, check, kind in CHECKS[:3] if args.seller_only else CHECKS:
            detail = check(bench)
            report['checks'][name] = {'result': 'pass', 'kind': kind, **(detail or {})}
    except BaseException:
        report['failed_after'] = list(report['checks'])
        report['last_checks'] = bench.history()[-5:]
        report['diagnostics'] = bench.diagnostics()
        print(json.dumps(report, indent=2))
        args.seller_only = False
        raise
    finally:
        if args.seller_only:
            report['workspace'] = str(bench.parent)
        else:
            bench.schedule.uninstall()
            shutil.rmtree(bench.parent, ignore_errors=True)
    report['seconds'] = round(time.monotonic() - started, 1)
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()

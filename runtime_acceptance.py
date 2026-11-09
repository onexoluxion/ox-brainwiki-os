"""Real backend and MCP acceptance using only disposable, invented documents."""
import asyncio
import json
from pathlib import Path
import shutil
import sqlite3
import sys
import tempfile
import time

from fastmcp import Client
from fastmcp.client.transports import StdioTransport
import sqlite_vec
from ox_retrieval import BASE, Retrieval


def payload(result):
    if result.structured_content is not None:
        return result.structured_content
    return json.loads(result.content[0].text)


async def through_mcp(app, config):
    transport = StdioTransport(command=sys.executable,
                              args=[str(BASE/'ox_retrieval.py'), 'serve', '--config', str(config)])
    async with Client(transport) as client:
        assert {t.name for t in await client.list_tools()} == {'search', 'read', 'list', 'status'}
        state = payload(await client.call_tool('status', {}))
        assert state['fresh'] and state['completeness']['status'] == 'complete'
        query = {'query': 'Why was the aurora sensor calibration postponed?',
                 'mode': 'semantic', 'scope': 'notes/target'}
        result = payload(await client.call_tool('search', query))
        assert [r['path'] for r in result['results']] == ['notes/target/answer.md']
        original = payload(await client.call_tool('read', {'path': 'notes/target/answer.md'}))
        assert original['untrusted_content'] is True and 'reference lamp failed' in original['content']
        exact = payload(await client.call_tool('search', {'query': 'SYN-471', 'mode': 'exact'}))
        assert exact['results'][0]['path'] == 'notes/target/answer.md'
        excluded = payload(await client.call_tool('search', {'query': 'EXCLUDED-SYN-993', 'mode': 'exact'}))
        assert not excluded['results']
        receipt = app.state/'receipt.json'
        with app.state_guard():
            saved = receipt.read_bytes()
            receipt.write_bytes(b'{')
        try:
            state = payload(await client.call_tool('status', {}))
            assert not state['fresh'] and state['reason'] == 'receipt_invalid'
            assert str(app.root) not in json.dumps(state) and str(app.state) not in json.dumps(state)
            exact = payload(await client.call_tool('search', {'query': 'SYN-471', 'mode': 'exact'}))
            assert exact['results']
            try:
                await client.call_tool('search', query)
            except Exception as error:
                assert 'index_unavailable' in str(error)
                assert str(app.state) not in str(error)
            else:
                raise AssertionError('semantic search accepted an invalid receipt')
        finally:
            with app.state_guard():
                receipt.write_bytes(saved)


def run():
    started = time.monotonic()
    with tempfile.TemporaryDirectory(prefix='ox-runtime-') as temporary:
        parent = Path(temporary)
        root, state = parent/'source', parent/'state'
        for directory in ('notes/target', 'notes/other', 'notes/private'):
            (root/directory).mkdir(parents=True)
        (root/'notes/target/answer.md').write_text(
            '# SYN-471\nThe aurora sensor calibration was postponed because the reference lamp failed.\n',
            encoding='utf-8')
        for number in range(60):
            (root/f'notes/other/check-{number}.md').write_text(
                f'# Station {number}\nCalibration maintenance and sensor alignment checklist.\n',
                encoding='utf-8')
        (root/'notes/private/hidden.md').write_text('EXCLUDED-SYN-993', encoding='utf-8')
        app = Retrieval(root, state)
        # Reuse only this repository's public model artifacts when available.
        cache = BASE/'.state-secure'/'models'
        if cache.is_dir():
            with app.state_guard():
                shutil.copytree(cache, state/'models')
        before = app.inventory()
        indexed = app.index()
        assert indexed['fresh'] and indexed['completeness']['documents'] == 61
        config = parent/'config.json'
        config.write_text(json.dumps({'root': str(root), 'state': str(state),
                                      'allow': ['notes'], 'exclude': ['notes/private']}), encoding='utf-8')
        asyncio.run(through_mcp(app, config))
        with app.state_guard():
            db = sqlite3.connect(state/'bm'/'memory.db')
            try:
                db.enable_load_extension(True)
                sqlite_vec.load(db)
                db.enable_load_extension(False)
                row = db.execute(
                    'SELECT c.id FROM search_vector_chunks c JOIN entity e ON e.id=c.entity_id '
                    'WHERE e.file_path=? LIMIT 1', ('notes/target/answer.md',),
                ).fetchone()
                assert row is not None
                db.execute('DELETE FROM search_vector_embeddings WHERE rowid=?', (row[0],))
                db.commit()
            finally:
                db.close()
        state_result = app.status()
        assert not state_result['fresh'] and state_result['completeness']['invalid_chunks'] > 0
        assert app.inventory() == before
    print(json.dumps({'real_backend': 'pass', 'mcp_exact_semantic_read_status': 'pass',
                      'scoped_search_with_60_distractors': 'pass', 'excluded_document': 'pass',
                      'corrupt_receipt_mcp': 'pass', 'missing_vector': 'pass',
                      'source_hashes_unchanged': True, 'seconds': round(time.monotonic()-started, 2)}))


if __name__ == '__main__':
    run()

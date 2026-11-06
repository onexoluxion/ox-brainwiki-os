import asyncio
import json
from pathlib import Path
import shutil
import tempfile
import time
from fastmcp import Client
from ox_retrieval import Retrieval, BASE

def run():
    r=Retrieval(); before=r.inventory(); started=time.perf_counter()
    assert r.search('Why was the delivery of cups postponed?')['results'][0]['path']=='notes/shipment.md'
    vector_seconds=time.perf_counter()-started
    assert 'WO-2048' in r.backend('tool','search','--mode','text','--json','--local','--project','main','--','WO-2048')
    assert 'SECRET-EXCLUDED-999' not in r.backend('tool','search','--mode','text','--json','--local','--project','main','--','SECRET-EXCLUDED-999')
    assert r.inventory()==before
    with tempfile.TemporaryDirectory(dir=BASE/'.state') as tmp:
        root=Path(tmp)/'source'; shutil.copytree(BASE/'fixtures',root,symlinks=True)
        # Separate source copy; reuse isolated model cache through candidate state.
        r=Retrieval(root,Path(tmp)/'index')
        r.index(); initial=r.inventory(); assert r.status()['fresh']
        p=root/'notes'/'shipment.md'; p.write_text('# WO-2048\nThe ceramic cups delivery is cancelled after the packaging broke.',encoding='utf-8')
        assert not r.status()['fresh']
        try: r.search('cups')
        except RuntimeError: pass
        else: raise AssertionError('stale search allowed')
        changed=r.inventory(); r.index(); assert changed==r.inventory()
        assert 'cancelled' in r.search('ceramic cups delivery')['results'][0]['excerpt']
        p.rename(root/'notes'/'renamed.md'); r.index()
        assert r.search('ceramic cups delivery')['results'][0]['path']=='notes/renamed.md'
        (root/'notes'/'renamed.md').unlink(); r.index()
        assert not r.search('WO-2048','exact')['results']
        raw=json.loads(r.backend('tool','search','--mode','text','--json','--local','--project','main','--','WO-2048'))
        assert not raw['results'], raw
    print(json.dumps({'backend_exact':'pass','vector_paraphrase':'pass','vector_seconds':vector_seconds,'original_hashes':before,'modification_rename_deletion':'pass','excluded_backend_search':'pass'},indent=2))

if __name__=='__main__': run()

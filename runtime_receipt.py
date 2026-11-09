"""Private, bounded receipt persistence; no user content or exception text in errors."""
import json
import math
import os
from pathlib import Path
import re
import tempfile

MAX_RECEIPT_BYTES = 2 * 1024 * 1024
SCHEMA = 1
HASH = re.compile(r'[0-9a-f]{64}\Z')


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('duplicate field')
        result[key] = value
    return result


def valid_receipt(data):
    fields = {'schema', 'hashes', 'identity', 'indexed_at', 'vector_probe'}
    if not isinstance(data, dict) or set(data) != fields:
        return False
    if type(data['schema']) is not int or data['schema'] != SCHEMA:
        return False
    hashes, identity, timestamp = data['hashes'], data['identity'], data['indexed_at']
    if not isinstance(hashes, dict) or len(hashes) > 1000:
        return False
    if any(not isinstance(p, str) or not 1 <= len(p) <= 512
           or not isinstance(h, str) or not HASH.fullmatch(h) for p, h in hashes.items()):
        return False
    if (not isinstance(identity, dict) or not {'versions', 'scope'} <= identity.keys()
            or not 3 <= len(identity) <= 10000):
        return False
    versions, scope = identity['versions'], identity['scope']
    if (not isinstance(versions, dict) or set(versions) != {'basic-memory', 'fastmcp', 'fastembed'}
            or any(not isinstance(v, str) or not 1 <= len(v) <= 128 for v in versions.values())):
        return False
    if (not isinstance(scope, list) or len(scope) != 3
            or not isinstance(scope[0], str) or not 1 <= len(scope[0]) <= 2048):
        return False
    for prefixes in scope[1:]:
        if (not isinstance(prefixes, list) or len(prefixes) > 100
                or any(not isinstance(p, str) or not 1 <= len(p) <= 512 for p in prefixes)):
            return False
    for key, value in identity.items():
        if key in ('versions', 'scope'):
            continue
        if (not isinstance(key, str) or not 1 <= len(key) <= 2048
                or not isinstance(value, str) or not HASH.fullmatch(value)):
            return False
    if (type(timestamp) not in (float, int) or not 0 <= timestamp <= 1e12
            or not math.isfinite(timestamp)):
        return False
    return data['vector_probe'] is True


def read_receipt(path):
    try:
        with Path(path).open('rb') as stream:
            raw = stream.read(MAX_RECEIPT_BYTES + 1)
        if len(raw) > MAX_RECEIPT_BYTES:
            return None, 'receipt_oversized'
        data = json.loads(raw, object_pairs_hook=unique_object)
        if not valid_receipt(data):
            return None, 'receipt_invalid'
        return data, 'ready'
    except FileNotFoundError:
        return None, 'receipt_missing'
    except (OSError, ValueError, RecursionError):
        return None, 'receipt_invalid'


def write_receipt(path, data):
    if not valid_receipt(data):
        raise ValueError('invalid receipt')
    raw = json.dumps(data, allow_nan=False).encode('utf-8')
    if len(raw) > MAX_RECEIPT_BYTES:
        raise ValueError('receipt too large')
    path = Path(path)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode='wb', dir=path.parent,
                                         prefix='receipt-', suffix='.tmp', delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)

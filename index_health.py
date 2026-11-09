"""Bounded, read-only coverage checks for the pinned local SQLite backend."""
import hashlib
from contextlib import closing
from importlib.metadata import version, PackageNotFoundError
import os
from pathlib import Path
import re
import sqlite3
import time

EMBEDDING_IDENTITY = 'FastEmbedEmbeddingProvider:bge-small-en-v1.5:384'
MAX_DOCUMENTS = 1000
MAX_CHUNKS = 100000
QUERY_SECONDS = 2
PROGRESS_STEPS = 1000
BATCH_ROWS = 64
EMPTY_HASH = hashlib.sha256(b'').hexdigest()
DIGEST = re.compile(r'[0-9a-f]{64}\Z')


class _IndexLimit(Exception):
    pass


def _rows(cursor, limit, deadline):
    """Bound both database work and Python-side cursor consumption."""
    count = 0
    while True:
        if time.monotonic() > deadline:
            raise sqlite3.OperationalError('index deadline')
        batch = cursor.fetchmany(BATCH_ROWS)
        if not batch:
            return
        count += len(batch)
        if count > limit:
            raise _IndexLimit
        yield from batch
        del batch


def inspect_index(database, project_path, hashes):
    """Return counts/enums only; never initialize, repair or expose indexed text."""
    report = {
        'status': 'unknown', 'reason': 'index_unavailable',
        'documents': len(hashes), 'indexed_documents': 0,
        'missing_documents': 0, 'changed_documents': 0,
        'unexpected_documents': 0, 'incomplete_documents': 0,
        'chunks': 0, 'invalid_chunks': 0, 'extra_vectors': 0,
    }
    try:
        backend_version = version('basic-memory')
    except (PackageNotFoundError, OSError, ValueError, KeyError):
        return dict(report, reason='backend_metadata_unavailable')
    if backend_version != '1.0.0':
        return dict(report, reason='unsupported_backend')
    database = Path(database)
    if not database.is_file():
        return report
    try:
        import sqlite_vec
        with closing(sqlite3.connect(database.as_uri() + '?mode=ro', uri=True, timeout=1)) as db:
            # Load only the installed pinned dependency, never a configured extension.
            db.enable_load_extension(True)
            try:
                sqlite_vec.load(db)
            finally:
                db.enable_load_extension(False)
            db.execute('PRAGMA query_only = ON')
            db.execute('PRAGMA trusted_schema = OFF')
            deadline = time.monotonic() + QUERY_SECONDS
            db.set_progress_handler(lambda: int(time.monotonic() > deadline), PROGRESS_STEPS)
            db.execute('BEGIN')
            schema = db.execute(
                "SELECT substr(sql,1,4097) FROM sqlite_master WHERE type='table' AND name=?",
                ('search_vector_embeddings',),
            ).fetchone()
            if not schema or not isinstance(schema[0], str) or len(schema[0]) > 4096:
                return dict(report, reason='unsupported_schema')
            if not re.search(r'\bUSING\s+vec0\s*\(', schema[0], re.IGNORECASE):
                return dict(report, reason='unsupported_schema')
            projects = db.execute('SELECT id, substr(path,1,2049) FROM project LIMIT 101').fetchall()
            if len(projects) > 100:
                return dict(report, reason='index_limit')
            selected = [p[0] for p in projects if isinstance(p[1], str)
                        and os.path.normcase(os.path.normpath(p[1]))
                        == os.path.normcase(os.path.normpath(str(project_path)))]
            if len(selected) != 1:
                return dict(report, reason='project_unavailable')
            project_id = selected[0]
            entities = []
            indexed = {}
            for entity_id, name, digest, synced, deferred in _rows(db.execute(
                'SELECT id, substr(file_path,1,513), substr(checksum,1,65), '
                'substr(sync_checksum,1,65), vector_sync_deferred_at IS NOT NULL FROM entity '
                'WHERE project_id=? LIMIT ?', (project_id, MAX_DOCUMENTS + 1),
            ), MAX_DOCUMENTS, deadline):
                # Retain only metadata needed after the cursor is drained.
                entities.append((entity_id, name, deferred))
                indexed[name] = (digest, synced)
            vector_hashes = dict(_rows(db.execute(
                'SELECT rowid, substr(source_hash,1,65) FROM search_vector_embeddings '
                'WHERE project_id=? LIMIT ?', (project_id, MAX_CHUNKS + 1),
            ), MAX_CHUNKS, deadline))
            entity_ids = {item[0] for item in entities}
            chunk_ids, populated = set(), set()
            chunk_count = invalid_chunks = 0
            for chunk_id, entity_id, ready, model, store, digest in _rows(db.execute(
                'SELECT id, entity_id, substr(embedding_status,1,16), '
                'substr(embedding_model,1,256), substr(vector_index,1,32), '
                'substr(source_hash,1,65) FROM search_vector_chunks WHERE project_id=? LIMIT ?',
                (project_id, MAX_CHUNKS + 1),
            ), MAX_CHUNKS, deadline):
                chunk_count += 1
                chunk_ids.add(chunk_id)
                populated.add(entity_id)
                if (entity_id not in entity_ids or ready != 'ready'
                        or model != EMBEDDING_IDENTITY or store != 'sqlite-vec'
                        or not isinstance(digest, str) or not DIGEST.fullmatch(digest)
                        or vector_hashes.get(chunk_id) != digest):
                    invalid_chunks += 1
    except _IndexLimit:
        return dict(report, reason='index_limit')
    except (sqlite3.Error, OSError, ImportError, ValueError):
        return report

    # The backend may normalize staged frontmatter. Its sync checksum retains
    # the input bytes; either recorded file identity can match the source.
    report['indexed_documents'] = len(entities)
    report['chunks'] = chunk_count
    report['missing_documents'] = len(hashes.keys() - indexed.keys())
    report['unexpected_documents'] = len(indexed.keys() - hashes.keys())
    report['changed_documents'] = sum(digest not in indexed[p]
                                      for p, digest in hashes.items() if p in indexed)
    report['invalid_chunks'] = invalid_chunks
    report['extra_vectors'] = sum(chunk_id not in chunk_ids for chunk_id in vector_hashes)
    report['incomplete_documents'] = sum(
        bool(deferred) or (hashes.get(name) != EMPTY_HASH and entity_id not in populated)
        for entity_id, name, deferred in entities
    )
    failures = ('missing_documents', 'changed_documents', 'unexpected_documents',
                'incomplete_documents', 'invalid_chunks', 'extra_vectors')
    failed = len(indexed) != len(entities) or any(report[key] for key in failures)
    return dict(report, status='incomplete' if failed else 'complete',
                reason='index_incomplete' if failed else 'ready')

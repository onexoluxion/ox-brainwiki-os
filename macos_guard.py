"""Local account isolation for the native macOS runtime."""
from contextlib import closing, contextmanager
import ctypes
import errno
import fcntl
import os
from pathlib import Path
import select
import signal
import stat
import subprocess
import time
from unicodedata import normalize


ACL_TYPE_EXTENDED = 0x100
ACL_FIRST_ENTRY = 0
ACL_NEXT_ENTRY = -1
ACL_EXTENDED_DENY = 2
DIRECTORY = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW_ANY
NO_LINKS = os.O_NOFOLLOW_ANY | os.O_NONBLOCK
PATH_MAX = 1024

_libc = ctypes.CDLL('/usr/lib/libSystem.B.dylib', use_errno=True)
_libc.acl_get_fd_np.argtypes = [ctypes.c_int, ctypes.c_int]
_libc.acl_get_fd_np.restype = ctypes.c_void_p
_libc.acl_free.argtypes = [ctypes.c_void_p]
_libc.acl_free.restype = ctypes.c_int
_libc.acl_get_entry.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.POINTER(ctypes.c_void_p)]
_libc.acl_get_entry.restype = ctypes.c_int
_libc.acl_get_tag_type.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_int)]
_libc.acl_get_tag_type.restype = ctypes.c_int


def path_key(path):
    return normalize('NFC', os.fspath(path)).casefold()


@contextmanager
def open_verified(path, flags, mode=0o600, parent=None):
    fd = os.open(path.name if parent is not None else path, flags, mode, dir_fd=parent)
    try:
        raw = fcntl.fcntl(fd, fcntl.F_GETPATH, bytes(PATH_MAX))
        actual = os.fsdecode(raw.split(b'\0', 1)[0])
        if path_key(actual) != path_key(path):
            raise ValueError('path alias denied')
        yield fd
    finally:
        os.close(fd)


def reject_acl_grants(fd):
    """A macOS allow ACE can grant access beyond the POSIX permission bits."""
    acl = _libc.acl_get_fd_np(fd, ACL_TYPE_EXTENDED)
    if not acl:
        if ctypes.get_errno() == errno.ENOENT:
            return
        raise OSError(ctypes.get_errno(), 'file ACL unavailable')
    try:
        entry = ctypes.c_void_p()
        kind = ctypes.c_int()
        selector = ACL_FIRST_ENTRY
        while _libc.acl_get_entry(acl, selector, ctypes.byref(entry)) == 0:
            if (_libc.acl_get_tag_type(entry, ctypes.byref(kind)) != 0
                    or kind.value != ACL_EXTENDED_DENY):
                raise ValueError('state ACL grants access')
            selector = ACL_NEXT_ENTRY
        if ctypes.get_errno() != errno.EINVAL:
            raise OSError(ctypes.get_errno(), 'file ACL unavailable')
    finally:
        _libc.acl_free(acl)


def validate_state_parent(path):
    # Root-owned sticky directories such as /private/var/folders protect
    # entries owned by root or this user from rename by other users.
    for part in (*reversed(path.parents), path):
        with open_verified(part, DIRECTORY) as fd:
            info = os.fstat(fd)
            sticky = info.st_uid == 0 and info.st_mode & stat.S_ISVTX
            if info.st_uid not in (0, os.geteuid()) or (info.st_mode & 0o022 and not sticky):
                raise ValueError('untrusted state ancestor')
            reject_acl_grants(fd)


@contextmanager
def locked_state(path, scanned=None):
    """Yield (lock, identity). Skip the tree scan when `scanned` is this directory's identity."""
    validate_state_parent(path.parent)
    with open_verified(path.parent, DIRECTORY) as parent:
        try:
            os.mkdir(path.name, 0o700, dir_fd=parent)
        except FileExistsError:
            pass
        with open_verified(path, DIRECTORY, parent=parent) as state:
            info = os.fstat(state)
            identity = (info.st_dev, info.st_ino)
            if info.st_uid != os.geteuid() or info.st_mode & 0o077:
                raise ValueError('state directory must be private to its owner')
            reject_acl_grants(state)
            lock_path = path / 'operation.lock'
            with open_verified(lock_path, os.O_CREAT | os.O_RDWR | NO_LINKS, parent=state) as lock:
                info = os.fstat(lock)
                if (not stat.S_ISREG(info.st_mode) or info.st_nlink != 1
                        or info.st_uid != os.geteuid() or info.st_mode & 0o077):
                    raise ValueError('untrusted state lock')
                reject_acl_grants(lock)
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                for entry in path.rglob('*') if identity != scanned else ():
                    info = entry.lstat()
                    if (info.st_uid != os.geteuid()
                            or not (stat.S_ISDIR(info.st_mode)
                                    or (stat.S_ISREG(info.st_mode) and info.st_nlink == 1))):
                        raise ValueError('linked or untrusted state entry')
                yield lock, identity


def verify_source(fd):
    info = os.fstat(fd)
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
        raise ValueError('linked or non-regular source denied')


def paths_overlap(root, state):
    """Also check filesystem identities, including macOS volume aliases."""
    source = root.stat()
    if any(os.path.samestat(source, parent.stat()) for parent in state.parents):
        return True
    try:
        index = state.lstat()
    except FileNotFoundError:
        return False
    return any(os.path.samestat(index, part.stat()) for part in (root, *root.parents))


def wait_for_backend(proc, timeout, exceeded):
    """Observe the exit before reaping so the process group ID cannot be reused."""
    deadline = time.monotonic() + timeout
    with closing(select.kqueue()) as queue:
        event = select.kevent(proc.pid, filter=select.KQ_FILTER_PROC,
                             flags=select.KQ_EV_ADD | select.KQ_EV_ONESHOT,
                             fflags=select.KQ_NOTE_EXIT)
        try:
            queue.control([event], 0, 0)
        except ProcessLookupError:
            return  # The child exited before it could be registered.
        while not exceeded.is_set():
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise subprocess.TimeoutExpired(proc.args, timeout)
            if queue.control(None, 1, min(0.05, remaining)):
                return


def stop_backend(proc):
    try:
        os.killpg(proc.pid, signal.SIGKILL)
    except (ProcessLookupError, PermissionError):
        # Darwin may return EPERM for a group containing only its zombie
        # leader. A still-running leader will fail the bounded wait below.
        pass
    proc.wait(timeout=5)

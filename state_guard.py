"""Windows single-user state isolation. Same-token hostile processes are not sandboxed."""
from contextlib import contextmanager
from pathlib import Path
import threading
import functools
import win32api, win32con, win32file, win32security, pywintypes

SID = win32security.GetTokenInformation(win32security.OpenProcessToken(win32api.GetCurrentProcess(), win32con.TOKEN_QUERY), win32security.TokenUser)[0]
TRUSTED = {win32security.ConvertSidToStringSid(SID), 'S-1-5-18', 'S-1-5-32-544'}

def validate_acl(path):
    sd=win32security.GetFileSecurity(str(path),win32security.OWNER_SECURITY_INFORMATION|win32security.DACL_SECURITY_INFORMATION)
    if win32security.ConvertSidToStringSid(sd.GetSecurityDescriptorOwner()) not in TRUSTED:
        raise ValueError('untrusted state owner')
    acl=sd.GetSecurityDescriptorDacl()
    if acl is None: raise ValueError('unrestricted state denied')
    for i in range(acl.GetAceCount()):
        ace=acl.GetAce(i)
        if ace[0][0] != win32security.ACCESS_ALLOWED_ACE_TYPE or win32security.ConvertSidToStringSid(ace[2]) not in TRUSTED:
            raise ValueError('state ACL must allow only owner, SYSTEM and Administrators')

def create_private(path):
    acl=win32security.ACL()
    for sid in TRUSTED:
        acl.AddAccessAllowedAceEx(win32security.ACL_REVISION,3,0x1F01FF,win32security.ConvertStringSidToSid(sid))
    sd=win32security.SECURITY_DESCRIPTOR();sd.SetSecurityDescriptorDacl(1,acl,0)
    sd.SetSecurityDescriptorOwner(SID,0)
    sd.SetSecurityDescriptorControl(win32security.SE_DACL_PROTECTED,win32security.SE_DACL_PROTECTED)
    sa=pywintypes.SECURITY_ATTRIBUTES();sa.SECURITY_DESCRIPTOR=sd
    win32file.CreateDirectory(str(path),sa)

def guarded(method):
    @functools.wraps(method)
    def call(self,*args,**kwargs):
        with self.state_guard(): return method(self,*args,**kwargs)
    return call

@contextmanager
def state_guard(app):
    from ox_retrieval import pinned_directories
    if getattr(app._guard_local,'depth',0):
        yield;return
    # Parent is operator-selected and must already exist: never create arbitrary ancestor trees.
    with pinned_directories(app.state.parent):
        if not app.state.exists():create_private(app.state)
        with pinned_directories(app.state):
            validate_acl(app.state)
            # Existing state is trusted operator data, never a writable source subtree.
            for p in app.state.rglob('*'):
                if p.is_symlink() or p.is_junction():raise ValueError('linked state denied')
                if p.is_file() and p.stat().st_nlink != 1:raise ValueError('linked state file denied')
                validate_acl(p)
            lock=app.state/'operation.lock'
            handle=win32file.CreateFile(str(lock),win32con.GENERIC_READ|win32con.GENERIC_WRITE,0,None,win32con.OPEN_ALWAYS,win32con.FILE_ATTRIBUTE_NORMAL|0x00200000,None)
            try:
                app._guard_local.depth=1
                yield
            finally:
                app._guard_local.depth=0
                handle.Close()

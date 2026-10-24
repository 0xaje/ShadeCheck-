"""Private-by-default local artifacts; explicit publication is a separate act.

POSIX modes do not replace Windows ACLs, encryption, or a trusted local account.
"""
import os
from pathlib import Path


def private_open(path, *, exclusive=False):
    path = Path(path)
    # Only change directories we create, not an existing developer-owned tree.
    missing = []
    parent = path.parent
    while not parent.exists():
        missing.append(parent)
        parent = parent.parent
    for directory in reversed(missing):
        directory.mkdir(mode=0o700, exist_ok=True)
    flags = os.O_WRONLY | os.O_CREAT | (os.O_EXCL if exclusive else os.O_TRUNC)
    flags |= getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(path, flags, 0o600)
    try:
        if os.name == "posix":
            os.fchmod(descriptor, 0o600)
        return os.fdopen(descriptor, "w", encoding="utf-8")
    except BaseException:
        os.close(descriptor)
        raise


def private_write(path, content):
    with private_open(path) as output:
        output.write(content)

"""Shared portable storage and a reentrant, cross-process workspace lock."""
from contextlib import contextmanager
from pathlib import Path
import functools
import hashlib
import json
import os
import re
import tempfile
import threading

from .paths import ROOT, SKILL, HOME, WORK
from . import filelock

_mutex = threading.RLock()
_local = threading.local()
# Snapshot keys: project files are project-relative; skill and toolchain files carry a prefix.
PREFIXES = (('skill:', SKILL), ('toolchain:', HOME))


def effect_id(value):
    if not isinstance(value, str) or not re.fullmatch(r'VFX_[A-Za-z0-9_]+', value):
        raise ValueError('Expected an effect ID such as VFX_Fire_Explosion')
    return value


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()).hexdigest()


def file_hash(path):
    path = Path(path)
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None


def relative(path):
    # Normalise without following symlinks first: a venv's python links outside the toolchain.
    for candidate in (Path(os.path.abspath(path)), Path(path).resolve()):
        if candidate.is_relative_to(ROOT):
            return candidate.relative_to(ROOT).as_posix()
        for prefix, base in PREFIXES:
            if candidate.is_relative_to(base):
                return prefix + candidate.relative_to(base).as_posix()
    raise ValueError(f'{path} is outside the project, the skill and the toolchain')


def absolute(name):
    for prefix, base in PREFIXES:
        if name.startswith(prefix):
            return base / name[len(prefix):]
    return ROOT / name


def snapshot(paths):
    return {relative(p): file_hash(p) for p in sorted(set(map(Path, paths)))}


def unchanged(files):
    return all(file_hash(absolute(name)) == sha and sha is not None for name, sha in files.items())


def save_json(path, value):
    from .ownership import guard
    path = guard(Path(path), ROOT / 'vfx')  # every store is inside the workspace; never follow a link out of it
    path.parent.mkdir(parents=True, exist_ok=True)
    # A fresh, unpredictable temporary file (created exclusively, so no pre-placed link can redirect the write),
    # then an atomic rename over the final path.
    handle, name = tempfile.mkstemp(prefix=path.name + '.', suffix='.tmp', dir=path.parent)
    temporary = Path(name)
    try:
        with os.fdopen(handle, 'w', encoding='utf-8') as stream:
            stream.write(json.dumps(value, ensure_ascii=False, indent=2) + '\n')
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)
    return path


@contextmanager
def project_lock():
    with _mutex:
        if getattr(_local, 'depth', 0):
            _local.depth += 1
            try:
                yield
            finally:
                _local.depth -= 1
            return
        path = WORK / 'project.lock'
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('a') as stream:
            filelock.acquire(stream)
            _local.depth = 1
            try:
                yield
            finally:
                _local.depth = 0
                filelock.release(stream)


def locked(function):
    @functools.wraps(function)
    def run(*args, **kwargs):
        with project_lock():
            return function(*args, **kwargs)
    return run

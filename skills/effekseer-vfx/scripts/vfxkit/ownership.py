"""Which effects and files in a workspace this skill built, so it only ever deletes or replaces its own.

Standard library only: `vfx doctor` uses it before setup has installed anything.
"""
import hashlib
import json
import re
import unicodedata
from pathlib import Path

MARKER = 'effekseer-vfx'  # manifest `built_by` of every entry this skill compiled


def valid_id(rid):
    return isinstance(rid, str) and re.fullmatch(r'VFX_[A-Za-z0-9_]+', rid) is not None


def digest(path):
    path = Path(path)
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None


def owned(entry, root, work):
    """Built by this skill, so a full build may remove it once its source is gone.

    Current builds tag the entry (`built_by` plus `source` = its own vfx/src file). Workspaces built before the tag
    count only through a build receipt whose recorded .efkefc is still the file on disk. Anything else (another
    tool's entry, a hand-made effect, a malformed ID) is never owned and never touched.
    """
    rid = entry.get('id') if isinstance(entry, dict) else None
    if not valid_id(rid):
        return False
    if entry.get('built_by') == MARKER and entry.get('source') == f'vfx/src/{rid}.py':
        return True
    receipt = Path(work) / f'builds/{rid}.json'
    if not receipt.is_file():
        return False
    try:
        recorded = json.loads(receipt.read_text())['outputs'].get(f'vfx/effects/{rid}.efkefc')
    except (ValueError, KeyError, AttributeError, TypeError):
        return False
    return recorded is not None and recorded == digest(Path(root) / f'vfx/effects/{rid}.efkefc')


def unmanaged(root, work, manifest, ignore=()):
    """Effect files this skill did not build: unowned manifest entries and .efkefc files no entry names."""
    root = Path(root)
    named, files = set(), []
    for entry in manifest:
        rid = entry.get('id') if isinstance(entry, dict) else None
        named.add(rid)
        if rid in ignore or owned(entry, root, work):
            continue
        path = root / f'vfx/effects/{rid}.efkefc' if valid_id(rid) else None
        files.append(path if path and path.is_file() else None)
    files += [p for p in sorted((root / 'vfx/effects').glob('*.efkefc')) if p.stem not in named]
    return files  # None stands for an unowned entry whose effect file is missing or unnamed: dependencies unknown


def name_key(name):
    """Comparison key of a resource name: Unicode NFC, then case folded. The default macOS file system (and Windows)
    treat T_A.png and t_a.png, and the composed and decomposed forms of a name such as T_Ä.png, as one file."""
    return unicodedata.normalize('NFC', name).casefold()


def same_name(a, b):
    return name_key(a) == name_key(b)


def may_use(effect_file, name):
    """Whether an effect file (whose dependencies are not recorded) could reference resource `name`.

    .efkefc and .efk store resource paths as UTF-16LE text. The bytes are decoded (UTF-16LE at both alignments, and
    UTF-8) and compared as Unicode with case folded, so any spelling of the name counts; an unknown or unreadable file
    always counts as a user."""
    if effect_file is None:
        return True
    try:
        data = Path(effect_file).read_bytes()
    except OSError:
        return True
    wanted = name_key(name)
    texts = [data.decode('utf-16-le', errors='replace'), data[1:].decode('utf-16-le', errors='replace'),
             data.decode('utf-8', errors='replace')]
    return any(wanted in name_key(text) for text in texts)


def inside(path, folder):
    """`path` (after resolving symlinks) lies within `folder`."""
    return Path(path).resolve().is_relative_to(Path(folder).resolve())


def guard(path, folder):
    """Raise unless writing `path` stays inside `folder`: its parent resolves inside, and the file itself (when it exists
    or is a dangling link) resolves inside too. Writes follow symlinks, so this must run before every write."""
    path = Path(path)
    if not inside(path.parent, folder) or ((path.exists() or path.is_symlink()) and not inside(path, folder)):
        raise ValueError(f'{path} resolves outside {Path(folder).resolve()}; refusing to write it')
    return path


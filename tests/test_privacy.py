"""The published package carries no personal, machine-specific or secret data, in text or in image metadata.

Generic rules only, so this file itself discloses nothing: e-mail addresses, home and temporary paths, credential
formats, and PNG metadata chunks. Binary files of any other kind fail until they are reviewed and allowed here.
The publisher's brand may appear only in the LICENSE files, the plugin manifests and the top-level README files, and
the vendored bridge's upstream author only in its LICENSE, THIRD_PARTY_NOTICES.md and the README files.

A maintainer can add terms that must never ship (names, handles, private project names) in a file kept outside the
package and point EFFEKSEER_VFX_PRIVATE_TERMS at it (one term per line, case-insensitive); without it that check skips.
"""
import os
import re
import struct
from pathlib import Path

import pytest

from conftest import PACKAGE

PUBLISHER = 'kanaworks'
ATTRIBUTION = 'laodeng000'
SKIPPED_FOLDERS = {'__pycache__', '.pytest_cache', '.git'}
SKIPPED_FILES = {'.DS_Store'}  # Finder metadata; ignored by .gitignore, never published
THIS = Path(__file__).resolve()

EMAIL = re.compile(r'[\w.+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}\b')  # python@3.12 is not one
ALLOWED_EMAIL = re.compile(r'@(?:example\.(?:com|org|invalid)|users\.noreply\.github\.com)$', re.I)
LOCAL_PATH = re.compile(r'(?<![\w.])(?:/Users/[^/\s"\'`<>]+|/home/[^/\s"\'`<>]+|/root/|/private/(?:tmp|var)/|'
                        r'/var/folders/|[A-Za-z]:\\Users\\)', re.I)
CREDENTIAL = re.compile(r'(?:sk-[A-Za-z0-9_-]{20,}|sk-ant-[A-Za-z0-9_-]{10,}|gh[pousr]_[A-Za-z0-9]{20,}|github_pat_\w{20,}|'
                        r'AKIA[0-9A-Z]{16}|xox[abposr]-[A-Za-z0-9-]{10,}|AIza[0-9A-Za-z_-]{30,}|'
                        r'-----BEGIN [A-Z ]*PRIVATE KEY-----|'
                        r'(?:api[_-]?key|secret|token|password|passwd)["\']?\s*[:=]\s*["\']?[A-Za-z0-9_\-/+=]{16,})', re.I)
# PNG chunks that carry pixels only; text, EXIF, XMP and ICC profiles (which can name a person or a machine) do not.
PNG_SIGNATURE = b'\x89PNG\r\n\x1a\n'
PNG_PIXEL_CHUNKS = {b'IHDR', b'PLTE', b'tRNS', b'IDAT', b'IEND', b'gAMA', b'cHRM', b'sRGB', b'sBIT', b'pHYs'}
REVIEWED_BINARY_SUFFIXES = {'.png', '.jpg'}
# JPEG segments that carry pixels only; APP1 (EXIF, XMP), APP2 (ICC), APP13 (IPTC) and comments can name a person or a machine.
JPEG_PIXEL_MARKERS = {0xC0, 0xC1, 0xC2, 0xC4, 0xDB, 0xDD, 0xE0}


def files():
    for path in sorted(PACKAGE.rglob('*')):
        if path.is_file() and not SKIPPED_FOLDERS & set(path.relative_to(PACKAGE).parts) and path.name not in SKIPPED_FILES:
            yield path


def publisher_allowed(path):
    relative = path.relative_to(PACKAGE).as_posix()
    return relative in ('LICENSE', 'skills/effekseer-vfx/LICENSE', 'skills/vfx-review/LICENSE',
                        '.claude-plugin/plugin.json', '.claude-plugin/marketplace.json', 'docs/brand/README.md') or (
        '/' not in relative and path.name.upper().startswith('README'))


def attribution_allowed(path):
    relative = path.relative_to(PACKAGE).as_posix()
    return (relative.endswith('scripts/effekseer_ai/LICENSE') or path.name == 'THIRD_PARTY_NOTICES.md'
            or path.name.upper().startswith('README'))


def private_terms():
    source = os.environ.get('EFFEKSEER_VFX_PRIVATE_TERMS')
    if not source:
        return None
    lines = Path(source).expanduser().read_text(encoding='utf-8').splitlines()
    return [t.strip().lower() for t in lines if t.strip() and not t.lstrip().startswith('#')]


def text_hits(path, text, terms=()):
    lowered = text.lower()
    found = [m.group(0) for m in EMAIL.finditer(text) if not ALLOWED_EMAIL.search(m.group(0))]
    found += [m.group(0) for m in LOCAL_PATH.finditer(text)]
    found += [m.group(0)[:12] + '...' for m in CREDENTIAL.finditer(text)]
    if PUBLISHER in lowered and not publisher_allowed(path):
        found.append(PUBLISHER)
    if ATTRIBUTION in lowered and not attribution_allowed(path):
        found.append(ATTRIBUTION)
    found += [f'private term #{i + 1}' for i, term in enumerate(terms) if term in lowered]
    return found


def png_metadata(data):
    """Names of PNG chunks beyond pixel data (or a problem with the file's structure)."""
    if not data.startswith(PNG_SIGNATURE):
        return ['not a PNG']
    extra, offset, ended = [], len(PNG_SIGNATURE), False
    while offset + 8 <= len(data):
        length, kind = struct.unpack('>I4s', data[offset:offset + 8])
        if offset + 12 + length > len(data):
            return extra + [f'{kind.decode("latin-1")} chunk runs past the end of the file']
        if kind not in PNG_PIXEL_CHUNKS:
            extra.append(kind.decode('latin-1'))
        offset += 12 + length
        if kind == b'IEND':
            ended = length == 0
            break
    if not ended:
        extra.append('no valid IEND chunk')
    elif offset < len(data):
        extra.append(f'{len(data) - offset} bytes after IEND')
    return extra


def jpeg_metadata(data):
    """Names of JPEG segments beyond pixel data (JFIF header, tables, frame and scan are fine)."""
    if not data.startswith(b'\xff\xd8'):
        return ['not a JPEG']
    extra, offset = [], 2
    while offset + 4 <= len(data):
        if data[offset] != 0xFF:
            return extra + ['broken segment structure']
        marker = data[offset + 1]
        if marker == 0xDA:   # start of scan: entropy-coded pixels follow
            return extra
        length = struct.unpack('>H', data[offset + 2:offset + 4])[0]
        if marker not in JPEG_PIXEL_MARKERS:
            extra.append(f'segment 0x{marker:02X}')
        offset += 2 + length
    return extra + ['no scan']


def file_hits(path, terms=()):
    data = path.read_bytes()
    if path.suffix.lower() == '.png':
        return png_metadata(data)
    if path.suffix.lower() == '.jpg':
        return jpeg_metadata(data)
    try:
        text = data.decode('utf-8')
    except UnicodeDecodeError:
        return [f'unreviewed binary file ({path.suffix or "no suffix"}); review it and allow its type here']
    if '\0' in text:
        return ['unreviewed binary file (NUL bytes)']
    return text_hits(path, text, terms)


def test_scanner_catches_each_kind_of_leak_and_respects_the_allowlists():
    md = PACKAGE / 'notes.md'
    for leak in ('mail me at someone.private@gmail.com', 'see /Users/someone/project', 'cd /home/someone/game',
                 'C:\\Users\\someone\\game', 'log in /private/tmp/session', 'API_KEY = "abcdefghijklmnop1234"',
                 '{"api_key": "abcdefghijklmnop1234"}', "{'password': 'abcdefghijklmnop1234'}",
                 'token: ghp_abcdefghijklmnopqrstuvwxyz0123', '-----BEGIN OPENSSH PRIVATE KEY-----'):
        assert text_hits(md, leak), leak
    for fine in ("p = 'node/root/0'", 'contact@example.com', 'the ~/.cache/effekseer-vfx toolchain',
                 'res://scripts/Vfx.gd', 'git clone https://github.com/<owner>/effekseer-vfx-skill', 'brew install python@3.12'):
        assert not text_hits(md, fine), fine
    assert text_hits(md, 'made by ' + PUBLISHER) and not text_hits(PACKAGE / 'LICENSE', 'Copyright ' + PUBLISHER)
    assert text_hits(md, 'by ' + ATTRIBUTION) and not text_hits(PACKAGE / 'THIRD_PARTY_NOTICES.md', 'by ' + ATTRIBUTION)
    assert text_hits(md, 'Private Name here', ['private name']) == ['private term #1']
    clean = PNG_SIGNATURE + struct.pack('>I4s', 0, b'IEND') + b'\0' * 4
    tagged = PNG_SIGNATURE + struct.pack('>I4s', 4, b'tEXt') + b'Name' + b'\0' * 4 + struct.pack('>I4s', 0, b'IEND') + b'\0' * 4
    assert png_metadata(clean) == [] and png_metadata(tagged) == ['tEXt'] and png_metadata(clean + b'x')
    assert png_metadata(PNG_SIGNATURE)                                          # signature only: no IEND
    assert png_metadata(PNG_SIGNATURE + struct.pack('>I4s', 9999, b'IDAT') + b'short')  # truncated chunk


def test_no_file_in_the_package_leaks_personal_machine_or_secret_data():
    # This file holds the patterns and synthetic samples themselves (reviewed by hand: no real data).
    checked = [p for p in files() if p.resolve() != THIS]
    assert any(p.name == 'SKILL.md' for p in checked) and any(p.suffix == '.png' for p in checked)
    terms = private_terms() or []
    leaks = {p.relative_to(PACKAGE).as_posix(): found for p in checked if (found := file_hits(p, terms))}
    assert not leaks, f'private or unreviewed content: {leaks}'


def test_maintainer_private_terms_when_configured():
    terms = private_terms()
    if terms is None:
        pytest.skip('set EFFEKSEER_VFX_PRIVATE_TERMS to a term list kept outside the package')
    assert terms, 'the private term list is empty'

#!/bin/sh
# Install the effekseer-vfx toolchain into EFFEKSEER_VFX_HOME (default ~/.cache/effekseer-vfx). Safe to re-run.
#
#   sh setup.sh                   full mode: Python packages, Effekseer Core 1.80.7 and the .NET 9 runtime (macOS ARM64)
#   sh setup.sh --authoring-only  Python packages only: write recipes, lint, process textures (macOS or Linux)
#
# On Windows (Git Bash, MSYS2) this runs setup.ps1, which installs the Windows toolchain (x64 or ARM64).
#
# Needs Python 3.11+ (found automatically) or uv. Exit codes: 0 ok, 1 a download or install failed, 3 full mode on an
# unsupported system, 4 no suitable Python.
#
# The Effekseer and .NET archives (~250 MB in full mode) come from the official Effekseer and Microsoft releases and
# are checked against pinned SHA-256 sums; Python packages are pinned by version (requirements.lock.txt), not by hash.
# Nothing is installed outside EFFEKSEER_VFX_HOME. Godot 4 is not installed here. Concurrent runs that share one
# EFFEKSEER_VFX_HOME wait for each other (kernel file lock); every download and extraction goes to a private
# temporary path first.
set -eu
MODE=full
[ "${1:-}" = "--authoring-only" ] && MODE=authoring
SCRIPTS=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
case "$(uname -s)" in
  MINGW*|MSYS*|CYGWIN*)
    [ -n "${EFFEKSEER_VFX_HOME:-}" ] && EFFEKSEER_VFX_HOME=$(cygpath -w "$EFFEKSEER_VFX_HOME") && export EFFEKSEER_VFX_HOME
    exec powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$(cygpath -w "$SCRIPTS/setup.ps1")" "$@" ;;
esac
TOOLCHAIN=${EFFEKSEER_VFX_HOME:-$HOME/.cache/effekseer-vfx}
CORE_URL=https://github.com/effekseer/Effekseer/releases/download/1807/Effekseer1.80.7Win.zip
CORE_SHA256=6f059b9cce3a79c5bfe3df9c970cfe62fd72acf130083c7b81832d90f8d1335f
DOTNET_VERSION=9.0.20
# Microsoft's published SHA-512 for this archive (releases.json) is
# 5bb676b5bac2656eb7e8c847532505007b2154df0f6682e31b1681e35d1b757ca201559677c7e2bb197a6b7563bc584d7fcefb26344a9f8f2a390b41136a2702
DOTNET_URL=https://builds.dotnet.microsoft.com/dotnet/Runtime/$DOTNET_VERSION/dotnet-runtime-$DOTNET_VERSION-osx-arm64.tar.gz
DOTNET_SHA256=452dc0b41e7918873b46b922187691581846a179579c0284d56a50bff5e6f1e6
mkdir -p "$TOOLCHAIN/downloads"

# One setup at a time per toolchain: re-run this script while holding an exclusive kernel lock on a lock file. The
# kernel releases it when the process exits, so a crashed run never leaves a lock behind and nothing is deleted to
# take one over. flock(1) where it exists (Linux), else Python's fcntl (macOS ships no flock(1)).
LOCKFILE="$TOOLCHAIN/.setup.lock"
if [ -z "${EFFEKSEER_VFX_SETUP_LOCKED:-}" ]; then
  export EFFEKSEER_VFX_SETUP_LOCKED=1
  if command -v flock >/dev/null 2>&1; then
    exec flock "$LOCKFILE" sh "$0" "$@"
  elif command -v python3 >/dev/null 2>&1; then
    exec python3 -c 'import fcntl, os, sys
lock = open(sys.argv[1], "a"); fcntl.flock(lock, fcntl.LOCK_EX); os.set_inheritable(lock.fileno(), True)
os.execvp("sh", ["sh"] + sys.argv[2:])' "$LOCKFILE" "$0" "$@"
  else
    echo "Neither flock nor python3 is available to lock $LOCKFILE; do not run two setups at once." >&2
  fi
fi
WORKDIR=$(mktemp -d "$TOOLCHAIN/downloads/.setup.XXXXXX")
trap 'rm -rf "$WORKDIR"' EXIT INT TERM

sha256() { if command -v shasum >/dev/null 2>&1; then shasum -a 256 "$1" | cut -d' ' -f1; else sha256sum "$1" | cut -d' ' -f1; fi; }
# fetch URL SHA256 TARGET: reuse a verified copy, else download privately, verify, then move into place.
fetch() {
  if [ -f "$3" ] && [ "$(sha256 "$3")" = "$2" ]; then return 0; fi
  curl -L --fail -o "$WORKDIR/download" "$1"
  [ "$(sha256 "$WORKDIR/download")" = "$2" ] || { echo "Checksum mismatch for $1" >&2; exit 1; }
  mv "$WORKDIR/download" "$3"
}

if [ "$MODE" = full ] && { [ "$(uname -s)" != Darwin ] || [ "$(uname -m)" != arm64 ]; }; then
  echo "Full mode (EffekseerCore build + Godot review) is verified on macOS ARM64 and Windows x64 only." >&2
  echo "On this system run: sh $0 --authoring-only" >&2
  exit 3
fi

# Python 3.11+ is required (the pinned numpy, Pillow and pythonnet need it). uv provides one by itself; otherwise use
# the newest python3.x on PATH or in the usual Homebrew locations. macOS's own /usr/bin/python3 is 3.9 and too old.
modern() { "$1" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)' >/dev/null 2>&1; }
find_python() {
  for candidate in python3.13 python3.12 python3.11 /opt/homebrew/bin/python3 /usr/local/bin/python3 python3; do
    found=$(command -v "$candidate" 2>/dev/null) || continue
    if modern "$found"; then echo "$found"; return 0; fi
  done
  return 1
}

echo "== Python packages -> $TOOLCHAIN/venv" >&2
# An environment from an older Python (or a broken earlier attempt) is replaced, never reused.
if [ -e "$TOOLCHAIN/venv" ] && ! modern "$TOOLCHAIN/venv/bin/python"; then
  echo "Replacing $TOOLCHAIN/venv: it is missing, broken or older than Python 3.11" >&2
  rm -rf "$TOOLCHAIN/venv"
fi
if [ ! -x "$TOOLCHAIN/venv/bin/python" ]; then
  if command -v uv >/dev/null 2>&1; then
    uv venv --python 3.12 "$TOOLCHAIN/venv" >&2
  elif PYTHON=$(find_python); then
    "$PYTHON" -m venv "$TOOLCHAIN/venv"
  else
    echo "Python 3.11 or newer is required and none was found (macOS's built-in python3 is 3.9)." >&2
    echo "Install one of them, then run this script again:" >&2
    echo "  uv (manages its own Python):  https://docs.astral.sh/uv/getting-started/installation/" >&2
    echo "  or Homebrew Python:           brew install python@3.12" >&2
    exit 4
  fi
fi
if ! { if command -v uv >/dev/null 2>&1; then uv pip install --python "$TOOLCHAIN/venv/bin/python" -r "$SCRIPTS/requirements.lock.txt" >&2
       else "$TOOLCHAIN/venv/bin/python" -m pip install --quiet -r "$SCRIPTS/requirements.lock.txt" >&2; fi; }; then
  echo "Installing the Python packages failed; fix the error above and run this script again (it resumes)." >&2
  exit 1
fi

if [ "$MODE" = full ]; then
  if [ ! -f "$TOOLCHAIN/effekseer/Effekseer1.80.7Win/Tool/bin/EffekseerCore.dll" ]; then
    echo "== Effekseer 1.80.7 (official release; only its managed Core assemblies are used)" >&2
    ARCHIVE="$TOOLCHAIN/downloads/Effekseer1.80.7Win.zip"
    fetch "$CORE_URL" "$CORE_SHA256" "$ARCHIVE"
    mkdir "$WORKDIR/effekseer"
    unzip -q "$ARCHIVE" -d "$WORKDIR/effekseer"
    rm -rf "$TOOLCHAIN/effekseer"
    mv "$WORKDIR/effekseer" "$TOOLCHAIN/effekseer"
  fi
  if [ ! -x "$TOOLCHAIN/dotnet/dotnet" ]; then
    echo "== .NET $DOTNET_VERSION runtime (official Microsoft archive)" >&2
    ARCHIVE="$TOOLCHAIN/downloads/dotnet-runtime-$DOTNET_VERSION-osx-arm64.tar.gz"
    fetch "$DOTNET_URL" "$DOTNET_SHA256" "$ARCHIVE"
    mkdir "$WORKDIR/dotnet"
    tar -xzf "$ARCHIVE" -C "$WORKDIR/dotnet"
    rm -rf "$TOOLCHAIN/dotnet"
    mv "$WORKDIR/dotnet" "$TOOLCHAIN/dotnet"
  fi
fi
sh "$SCRIPTS/vfx" doctor

"""Load the official Effekseer Core assembly through Python.NET."""

from __future__ import annotations

import os
import sys
from importlib import resources
from pathlib import Path
from typing import Any

_core: Any | None = None


def editor_bin_directory() -> Path:
    """Return the configured directory containing ``EffekseerCore.dll``.

    A release build deliberately does not search local drives. This keeps host
    layout private and makes the selected Effekseer installation explicit.
    """
    configured = os.environ.get("EFFEKSEER_AI_BIN_DIR")
    if configured:
        directory = Path(configured).expanduser().resolve()
        if (directory / "EffekseerCore.dll").is_file():
            return directory
        raise RuntimeError(
            "EFFEKSEER_AI_BIN_DIR must point to a directory containing "
            "EffekseerCore.dll"
        )
    raise RuntimeError(
        "EffekseerCore.dll was not found. Set EFFEKSEER_AI_BIN_DIR to "
        "the official Effekseer Tool/bin directory."
    )


def runtime_config_path() -> Path:
    """Return the bundled .NET runtime configuration file."""
    resource = resources.files("effekseer_ai").joinpath(
        "runtime", "ea.runtimeconfig.json"
    )
    return Path(resource)


def load_core() -> Any:
    """Load and return the official static ``Effekseer.Core`` type."""
    global _core
    if _core is not None:
        return _core

    bin_directory = editor_bin_directory()
    os.environ.setdefault("PYTHONNET_RUNTIME", "coreclr")
    os.environ.setdefault(
        "PYTHONNET_CORECLR_RUNTIME_CONFIG", str(runtime_config_path())
    )
    if str(bin_directory) not in sys.path:
        sys.path.insert(0, str(bin_directory))

    import clr

    clr.AddReference(str(bin_directory / "EffekseerCore.dll"))
    from Effekseer import Core

    _core = Core
    return Core


def export_binary(path: Path, magnification: float = 1.0) -> None:
    """Export the current Core document as an Effekseer runtime ``.efk`` file."""
    core = load_core()
    from Effekseer.Binary import Exporter
    from System.IO import File

    path.parent.mkdir(parents=True, exist_ok=True)
    File.WriteAllBytes(str(path), Exporter().Export(core.Root, magnification))

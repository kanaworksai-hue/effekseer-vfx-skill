"""The project's effect library: one recipe source per effect in vfx/src/<ID>.py.

Each source defines `recipe()` returning one `effect(...)` dict whose id equals the file name. Files whose
name starts with an underscore are shared helpers and can be imported by the others (`from _palette import *`).
Sources are loaded fresh on every call, so edits take effect without restarting anything.
"""
import importlib.abc
import importlib.util
import sys
from pathlib import Path
from .paths import ROOT

SRC = ROOT / 'vfx/src'


class HelperFinder(importlib.abc.MetaPathFinder):
    """Resolves `_name` helpers in vfx/src. It sits at the end of sys.meta_path and vfx/src is not on sys.path, so
    built-in modules, the standard library and installed packages always win; a helper only fills a name nothing
    else provides (name a helper `_ast.py` and you get the real `_ast`)."""

    def find_spec(self, name, path=None, target=None):
        if path is not None or not name.startswith('_'):
            return None
        source = SRC / f'{name}.py'
        return importlib.util.spec_from_file_location(name, source) if source.is_file() else None


_finder = HelperFinder()


def sources():
    return sorted(p for p in SRC.glob('VFX_*.py'))


def _forget_helpers():
    # A fresh load must see the helpers' current text; match the folder exactly, not a path prefix.
    for name in [n for n, m in sys.modules.items() if getattr(m, '__file__', None) and Path(m.__file__).resolve().parent == SRC.resolve()]:
        del sys.modules[name]


def load(path):
    path = Path(path)
    if _finder not in sys.meta_path:
        sys.meta_path.append(_finder)
    _forget_helpers()
    spec = importlib.util.spec_from_file_location(f'vfx_src_{path.stem}', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if not callable(getattr(module, 'recipe', None)):
        raise ValueError(f'{path.name}: define recipe() returning effect(...)')
    recipe = module.recipe()
    if not isinstance(recipe, dict) or recipe.get('id') != path.stem:
        raise ValueError(f'{path.name}: recipe() must return effect(...) whose id is {path.stem!r}, got {recipe.get("id") if isinstance(recipe, dict) else recipe!r}')
    return recipe


def describe(error):
    return f'{type(error).__name__}: {error}'


def library():
    """Every recipe; any source that fails to load fails the call (full builds and full lint need all of them)."""
    return [load(p) for p in sources()]


def partial(ids=None):
    """Recipes for `ids` must load; the rest are loaded best-effort as context for cross-effect checks.

    Returns (selected, context, unloaded) where `unloaded` maps a file that failed to load to its error, so one
    half-written effect does not block work on the others.
    """
    wanted = set(ids or [])
    selected, context, unloaded = [], [], {}
    for path in sources():
        if path.stem in wanted:
            recipe = load(path)
            selected.append(recipe)
            context.append(recipe)
            continue
        try:
            context.append(load(path))
        except Exception as error:
            unloaded[path.stem] = describe(error)
    unknown = sorted(wanted - {r['id'] for r in selected})
    if unknown:
        raise ValueError(f'Unknown effect IDs: {unknown} (no vfx/src/<ID>.py)')
    return selected, context, unloaded


def get(rid):
    path = SRC / f'{rid}.py'
    if not path.is_file():
        raise ValueError(f'Unknown effect ID: {rid} (no vfx/src/{rid}.py)')
    return load(path)

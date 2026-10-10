"""Command-line operations for the portable EffekseerCore bridge."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from collections.abc import Callable
from typing import Any

from .session import EffectSession


def _emit(value: Any) -> None:
    print(json.dumps(value, ensure_ascii=False, default=str))


def _open(path: str) -> EffectSession:
    return EffectSession.open(path)


def _new(args: argparse.Namespace) -> dict[str, Any]:
    session = EffectSession.new()
    session.save(args.path)
    return session.summary()


def _show(args: argparse.Namespace) -> dict[str, Any]:
    return _open(args.path).summary()


def _save(args: argparse.Namespace) -> dict[str, Any]:
    session = _open(args.source)
    session.save(args.destination)
    return session.summary()


def _node_list(args: argparse.Namespace) -> list[dict[str, Any]]:
    return _open(args.effect).node_list()


def _node_add(args: argparse.Namespace) -> dict[str, str]:
    session = _open(args.effect)
    path = session.add_node(args.parent, args.name)
    session.save()
    return {"path": path}


def _node_rename(args: argparse.Namespace) -> dict[str, str]:
    session = _open(args.effect)
    session.rename_node(args.node_path, args.name)
    session.save()
    return {"path": args.node_path}


def _node_remove(args: argparse.Namespace) -> dict[str, str]:
    session = _open(args.effect)
    session.remove_node(args.node_path)
    session.save()
    return {"removed": args.node_path}


def _node_move(args: argparse.Namespace) -> dict[str, str]:
    session = _open(args.effect)
    path = session.move_node(args.node_path, args.parent_path)
    session.save()
    return {"path": path}


def _property_list(args: argparse.Namespace) -> list[str]:
    return _open(args.effect).property_list(args.node_path)


def _property_get(args: argparse.Namespace) -> Any:
    return _open(args.effect).property_get(args.property_path)


def _property_set(args: argparse.Namespace) -> dict[str, Any]:
    session = _open(args.effect)
    session.property_set(args.property_path, json.loads(args.value))
    session.save()
    return {"value": session.property_get(args.property_path)}


def _image_import(args: argparse.Namespace) -> dict[str, str]:
    session = _open(args.effect)
    path = session.import_image(args.source, args.property_path)
    session.save()
    return {"path": path}


def _export(args: argparse.Namespace) -> dict[str, str]:
    return {"path": str(_open(args.effect).export(args.path, args.magnification))}


def _settings_list(args: argparse.Namespace) -> dict[str, Any]:
    return _open(args.effect).settings_list(args.node_path)


def _settings_set(args: argparse.Namespace) -> dict[str, str]:
    session = _open(args.effect)
    session.settings_set(args.node_path, args.panel, json.loads(args.values))
    session.save()
    return {"panel": args.panel}


def _curve_list(args: argparse.Namespace) -> list[dict[str, float | int]]:
    return _open(args.effect).curve_keys(args.curve_path)


def _curve_set(args: argparse.Namespace) -> dict[str, str]:
    session = _open(args.effect)
    session.curve_set_keys(args.curve_path, json.loads(args.keys))
    session.save()
    return {"curve": args.curve_path}


def _compile(args: argparse.Namespace) -> dict[str, Any]:
    from .authoring import compile_effect
    recipe = json.loads(Path(args.recipe).read_text(encoding="utf-8"))
    return {"ok": True, **compile_effect(recipe, args.source, args.runtime)}


def _texture_process(args: argparse.Namespace) -> dict[str, Any]:
    from .resources import process_texture
    return {"ok": True, **process_texture(args.source, args.output, args.size, mask=not args.color)}


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI parser without accessing an Effekseer installation."""
    parser = argparse.ArgumentParser(prog="effekseer-ai")
    commands = parser.add_subparsers(dest="command", required=True)

    def command(name: str, handler: Callable[[argparse.Namespace], Any]) -> argparse.ArgumentParser:
        subparser = commands.add_parser(name)
        subparser.set_defaults(handler=handler)
        return subparser

    command("new", _new).add_argument("path")
    command("open", _show).add_argument("path")
    save = command("save", _save)
    save.add_argument("source")
    save.add_argument("destination", nargs="?")

    node_list = command("node-list", _node_list)
    node_list.add_argument("effect")
    node_add = command("node-add", _node_add)
    node_add.add_argument("effect")
    node_add.add_argument("--parent", default="node/root")
    node_add.add_argument("--name")
    node_rename = command("node-rename", _node_rename)
    node_rename.add_argument("effect")
    node_rename.add_argument("node_path")
    node_rename.add_argument("name")
    node_remove = command("node-remove", _node_remove)
    node_remove.add_argument("effect")
    node_remove.add_argument("node_path")
    node_move = command("node-move", _node_move)
    node_move.add_argument("effect")
    node_move.add_argument("node_path")
    node_move.add_argument("parent_path")

    property_list = command("property-list", _property_list)
    property_list.add_argument("effect")
    property_list.add_argument("node_path")
    property_get = command("property-get", _property_get)
    property_get.add_argument("effect")
    property_get.add_argument("property_path")
    property_set = command("property-set", _property_set)
    property_set.add_argument("effect")
    property_set.add_argument("property_path")
    property_set.add_argument("value", help="A JSON value")

    image_import = command("image-import", _image_import)
    image_import.add_argument("effect")
    image_import.add_argument("source")
    image_import.add_argument("--property-path")
    export = command("export", _export)
    export.add_argument("effect")
    export.add_argument("path")
    export.add_argument("--magnification", type=float, default=1.0)

    settings_list = command("settings-list", _settings_list)
    settings_list.add_argument("effect")
    settings_list.add_argument("node_path")
    settings_set = command("settings-set", _settings_set)
    settings_set.add_argument("effect")
    settings_set.add_argument("node_path")
    settings_set.add_argument("panel")
    settings_set.add_argument("values", help="A JSON object")
    curve_list = command("curve-list", _curve_list)
    curve_list.add_argument("effect")
    curve_list.add_argument("curve_path")
    curve_set = command("curve-set", _curve_set)
    curve_set.add_argument("effect")
    curve_set.add_argument("curve_path")
    curve_set.add_argument("keys", help="A JSON keyframe list")
    compile_command = command("compile", _compile)
    compile_command.add_argument("recipe", help="JSON recipe; texture paths are relative to the current directory or absolute")
    compile_command.add_argument("source")
    compile_command.add_argument("--runtime")
    texture_command = command("texture-process", _texture_process)
    texture_command.add_argument("source")
    texture_command.add_argument("output")
    texture_command.add_argument("--size", type=int, default=256)
    texture_command.add_argument("--color", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        _emit(args.handler(args))
        return 0
    except Exception as error:
        _emit({"ok": False, "error": {"type": type(error).__name__, "message": str(error)}})
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

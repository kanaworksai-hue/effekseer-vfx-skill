"""The minimal effect-document lifecycle backed by Effekseer Core."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from shutil import copy2
from typing import Any

from .runtime import export_binary, load_core
from .settings import PANEL_LABELS, PANEL_ROOTS


@dataclass
class EffectSession:
    """A handle to the single Core document hosted by this Python process."""

    path: Path | None = None

    def __post_init__(self) -> None:
        self._nodes: dict[str, object] = {}
        self._index_existing_nodes()

    @classmethod
    def new(cls) -> "EffectSession":
        load_core().New()
        return cls()

    @classmethod
    def open(cls, path: str | Path) -> "EffectSession":
        effect_path = Path(path).resolve()
        if not effect_path.is_file():
            raise FileNotFoundError(effect_path)
        if not load_core().LoadFrom(str(effect_path)):
            raise ValueError(f"Effekseer cannot open: {effect_path}")
        return cls(effect_path)

    def save(self, path: str | Path | None = None) -> Path:
        effect_path = Path(path or self.path or "").resolve()
        if not str(effect_path):
            raise ValueError("A path is required for the first save")
        if effect_path.suffix.lower() != ".efkefc":
            raise ValueError("Effect files must use the .efkefc extension")
        effect_path.parent.mkdir(parents=True, exist_ok=True)
        load_core().SaveTo(str(effect_path))
        self.path = effect_path
        return effect_path

    def summary(self) -> dict[str, int | str | None]:
        root = load_core().Root
        return {
            "path": str(self.path) if self.path else None,
            "root_children": int(root.Children.Count),
        }

    def add_node(self, parent_path: str = "node/root", name: str | None = None) -> str:
        """Add a Core node and return its AI-facing path."""
        parent = self._node(parent_path)
        node = parent.AddChild()
        if name is not None:
            node.Name.SetValue(name)
        node_path = f"{parent_path}/{int(parent.Children.Count) - 1}"
        self._nodes[node_path] = node
        return node_path

    def node_list(self) -> list[dict[str, int | str]]:
        """List every non-root node currently known to the session."""
        return [
            {
                "path": path,
                "name": str(node.Name.Value),
                "children": int(node.Children.Count),
            }
            for path, node in self._nodes.items()
            if path != "node/root"
        ]

    def rename_node(self, node_path: str, name: str) -> None:
        """Rename a node through its Core string value."""
        if node_path == "node/root":
            raise ValueError("The root node cannot be renamed")
        self._node(node_path).Name.SetValue(name)

    def remove_node(self, node_path: str) -> None:
        """Remove a node and its descendants from the current document."""
        if node_path == "node/root":
            raise ValueError("The root node cannot be removed")
        node = self._node(node_path)
        if not node.Parent.RemoveChild(node):
            raise ValueError(f"Node is not attached: {node_path}")
        self._index_existing_nodes()

    def move_node(self, node_path: str, parent_path: str) -> str:
        """Move a node and return its new structural path."""
        if node_path == "node/root":
            raise ValueError("The root node cannot be moved")
        node = self._node(node_path)
        parent = self._node(parent_path)
        if node == parent or node.HasNode(parent, True):
            raise ValueError("A node cannot be moved into itself or its descendant")
        if not node.Parent.RemoveChild(node):
            raise ValueError(f"Node is not attached: {node_path}")
        parent.AddChild(node)
        self._index_existing_nodes()
        return f"{parent_path}/{int(parent.Children.Count) - 1}"

    def property_get(self, property_path: str) -> Any:
        """Read a public Core member without invoking arbitrary methods."""
        target, member = self._property_parent(property_path)
        return self._as_python(getattr(target, member))

    def property_set(self, property_path: str, value: Any) -> None:
        """Write an editable Core value or a public writable property."""
        node_path = next((path for path in sorted(self._nodes, key=len, reverse=True) if property_path.startswith(path + "/")), None)
        if node_path is not None:
            current = self._node(node_path)
            for member_name in property_path[len(node_path) + 1:].split("/"):
                member_info = current.GetType().GetProperty(member_name) if hasattr(current, "GetType") else None
                if member_info is not None and not self._is_exported_property(member_info):
                    raise ValueError(f"Import-only legacy property is not saved by this Core version: {property_path}. Use property-list to discover active fields.")
                current = getattr(current, member_name)
        target, member = self._property_parent(property_path)
        if member == "Value":
            self._assign_value(target, value)
            return

        property_info = target.GetType().GetProperty(member)
        if property_info is None or not property_info.CanWrite:
            raise ValueError(f"Property is not writable: {property_path}")
        setattr(target, member, value)

    def property_list(self, node_path: str, max_depth: int = 10) -> list[str]:
        """Discover editable leaf paths without walking parent/tree references."""
        leaves: list[str] = []
        skipped = {"Children", "Parent", "EditorNodeId", "Link", "DefaultValue", "IsValueChangedFromDefault", "IsValueAssigned", "DynamicEquation", "DynamicEquationMin", "DynamicEquationMax"}

        def walk(value: Any, path: str, depth: int) -> None:
            if value is None or isinstance(value, (bool, int, float, str)):
                leaves.append(path)
                return
            if depth == 0 or not hasattr(value, "GetType"):
                leaves.append(path)
                return
            value_type = value.GetType()
            if value_type.IsEnum:
                leaves.append(path)
                return
            if not (value_type.Namespace or "").startswith("Effekseer"):
                leaves.append(path)
                return
            for property_info in value_type.GetProperties():
                if (
                    not property_info.CanRead
                    or not self._is_exported_property(property_info)
                    or property_info.Name in skipped
                    or property_info.GetIndexParameters().Length != 0
                ):
                    continue
                try:
                    walk(getattr(value, property_info.Name), f"{path}/{property_info.Name}", depth - 1)
                except Exception:
                    continue
            for field_info in value_type.GetFields():
                if field_info.IsStatic or field_info.Name in skipped or field_info.Name.startswith("_"):
                    continue
                try:
                    walk(getattr(value, field_info.Name), f"{path}/{field_info.Name}", depth - 1)
                except Exception:
                    continue

        walk(self._node(node_path), node_path, max_depth)
        return sorted(set(leaves))

    @staticmethod
    def _is_exported_property(property_info: Any) -> bool:
        for attribute in property_info.GetCustomAttributes(False):
            if attribute.GetType().Name == "IOAttribute" and not attribute.Export:
                return False
        return True

    def settings_list(self, node_path: str) -> dict[str, dict[str, object]]:
        """Discover parameters grouped as they are in the editor's setting panels."""
        paths = self.property_list(node_path)
        return {
            panel: {
                "label": PANEL_LABELS[panel],
                "fields": [
                    path.removeprefix(f"{node_path}/{root}/")
                    for path in paths
                    if path.startswith(f"{node_path}/{root}/")
                ],
            }
            for panel, root in PANEL_ROOTS.items()
        }

    def settings_set(self, node_path: str, panel: str, values: dict[str, Any]) -> None:
        """Set a batch of panel-relative editable fields."""
        try:
            root = PANEL_ROOTS[panel]
        except KeyError as error:
            raise KeyError(f"Unknown settings panel: {panel}") from error
        for field, value in values.items():
            if field.startswith("/") or ".." in field.split("/"):
                raise ValueError(f"Invalid setting field: {field}")
            self.property_set(f"{node_path}/{root}/{field}", value)

    def curve_keys(self, curve_path: str) -> list[dict[str, float | int]]:
        """Read a scalar curve as JSON-friendly keyframe data."""
        curve = self._object_at_path(curve_path)
        return [
            {
                "frame": int(key.Frame), "value": float(key.Value),
                "left": [float(key.LeftX), float(key.LeftY)],
                "right": [float(key.RightX), float(key.RightY)],
                "interpolation": int(key.InterpolationType),
            }
            for key in curve.Keys
        ]

    def curve_set_keys(self, curve_path: str, keys: list[dict[str, Any]]) -> None:
        """Replace scalar FCurve keys using Core's add/remove commands."""
        import math
        frames = set()
        for data in keys:
            if "frame" not in data or "value" not in data:
                raise ValueError("Every curve key needs frame and value")
            frame = data["frame"]
            if isinstance(frame, bool) or int(frame) != frame or frame in frames:
                raise ValueError(f"Curve frames must be unique integers: {frame}")
            frames.add(frame)
            if not math.isfinite(float(data["value"])):
                raise ValueError("Curve values must be finite")
            if data.get("interpolation", 0) not in (0, 1):
                raise ValueError("Interpolation must be 0 (Bezier) or 1 (Linear)")
            for side in ("left", "right"):
                if side in data and (len(data[side]) != 2 or not all(math.isfinite(float(x)) for x in data[side])):
                    raise ValueError(f"Curve {side} handle must contain two finite coordinates")
        curve = self._object_at_path(curve_path)
        prepared = [self._new_curve_key(curve, data) for data in sorted(keys, key=lambda item: int(item["frame"]))]
        for key in list(curve.Keys):
            curve.RemoveKey(key)
        for key in prepared:
            curve.AddKey(key)

    def _new_curve_key(self, curve: object, data: dict[str, float | int]) -> object:
        from System import Activator, Array, Enum, Int32, Object, Single

        value_type = curve.GetType().GetGenericArguments()[0]
        value = Single(float(data["value"])) if value_type.Name == "Single" else Int32(int(data["value"]))
        key_type = curve.GetType().Assembly.GetType("Effekseer.Data.Value.FCurveKey`1")
        key_type = key_type.MakeGenericType(value_type)
        key = Activator.CreateInstance(key_type, Array[Object]([Int32(int(data["frame"])), value]))
        if "left" in data:
            key.SetLeft(Single(float(data["left"][0])), Single(float(data["left"][1])))
        if "right" in data:
            key.SetRight(Single(float(data["right"][0])), Single(float(data["right"][1])))
        if "interpolation" in data:
            enum_type = key.GetType().Assembly.GetType("Effekseer.Data.Value.FCurveInterpolation")
            key.SetInterpolationType(Enum.ToObject(enum_type, int(data["interpolation"])))
        key.Commit()
        return key

    def import_image(self, source: str | Path, property_path: str | None = None) -> str:
        """Copy an image beside the effect and optionally bind its Core path."""
        relative_path = self._copy_resource(
            source, {".png", ".jpg", ".jpeg", ".tga", ".dds", ".bmp"}
        )
        if property_path:
            image_path = self._object_at_path(property_path)
            if hasattr(image_path, "SetAbsolutePath"):
                image_path.SetAbsolutePath(str(self.path.parent / relative_path))
            else:
                self.property_set(property_path, relative_path)
        return relative_path

    def import_model(self, source: str | Path, property_path: str) -> str:
        """Copy a model into ``resources/`` and bind it through Core's path API."""
        relative_path = self._copy_resource(source, {".fbx", ".efkmodel"})
        absolute_path = self.path.parent / Path(relative_path)
        model_path = self._object_at_path(property_path)
        if not hasattr(model_path, "SetAbsolutePath"):
            raise ValueError(f"Property is not an Effekseer model path: {property_path}")
        model_path.SetAbsolutePath(str(absolute_path))
        return relative_path

    def export(self, path: str | Path, magnification: float = 1.0) -> Path:
        """Export the current document as a runtime `.efk` file."""
        output = Path(path).resolve()
        if output.suffix.lower() != ".efk":
            raise ValueError("Runtime exports must use the .efk extension")
        export_binary(output, magnification)
        return output

    def _index_existing_nodes(self) -> None:
        root = load_core().Root
        self._nodes.clear()
        self._nodes["node/root"] = root

        def visit(parent: object, parent_path: str) -> None:
            for index in range(parent.Children.Count):
                child = parent.Children[index]
                child_path = f"{parent_path}/{index}"
                self._nodes[child_path] = child
                visit(child, child_path)

        visit(root, "node/root")

    def _copy_resource(self, source: str | Path, extensions: set[str]) -> str:
        """Copy an approved asset to this effect's resource directory."""
        if self.path is None:
            raise ValueError("Save the effect before importing project resources")
        source_path = Path(source).resolve()
        if not source_path.is_file():
            raise FileNotFoundError(source_path)
        if source_path.suffix.lower() not in extensions:
            raise ValueError(f"Unsupported resource type: {source_path.suffix}")
        resources = self.path.parent / "resources"
        resources.mkdir(exist_ok=True)
        destination = resources / source_path.name
        copy2(source_path, destination)
        return destination.relative_to(self.path.parent).as_posix()

    def _node(self, node_path: str) -> object:
        try:
            return self._nodes[node_path]
        except KeyError as error:
            raise KeyError(f"Unknown node path: {node_path}") from error

    def _property_parent(self, property_path: str) -> tuple[object, str]:
        if not property_path.startswith("node/"):
            raise ValueError(f"Invalid property path: {property_path}")
        node_path = next(
            (path for path in sorted(self._nodes, key=len, reverse=True)
             if property_path.startswith(f"{path}/")),
            None,
        )
        if node_path is None:
            raise KeyError(f"Unknown node in property path: {property_path}")
        members = property_path[len(node_path) + 1 :].split("/")
        if any(not member or member.startswith("_") for member in members):
            raise ValueError(f"Invalid property path: {property_path}")

        target = self._node(node_path)
        for member in members[:-1]:
            target = getattr(target, member)
        return target, members[-1]

    def _object_at_path(self, property_path: str) -> object:
        target, member = self._property_parent(property_path)
        return getattr(target, member)

    def _assign_value(self, target: object, value: Any) -> None:
        """Write scalar values through nested Core editable-value wrappers."""
        if hasattr(target, "GetEnumType"):
            from System import Enum, Int32
            enum_type = target.GetEnumType()
            enum_value = Enum.Parse(enum_type, value) if isinstance(value, str) else Enum.ToObject(enum_type, Int32(value))
            if not Enum.IsDefined(enum_type, enum_value):
                raise ValueError(f"Invalid {enum_type.Name} value: {value}")
            target.SetValue(enum_value)
            return
        if hasattr(target, "SetValue"):
            target.SetValue(value)
            return
        property_info = target.GetType().GetProperty("Value")
        if property_info is None or not property_info.CanWrite:
            raise ValueError(f"Value is not writable on {target.GetType().FullName}")
        try:
            target.Value = value
        except TypeError:
            self._assign_value(target.Value, value)

    def _as_python(self, value: Any) -> Any:
        if value is None or isinstance(value, (bool, int, float, str)):
            return value
        if value.GetType().IsEnum:
            return str(value)
        property_info = value.GetType().GetProperty("Value")
        if property_info is not None and property_info.CanRead:
            return self._as_python(value.Value)
        return str(value)

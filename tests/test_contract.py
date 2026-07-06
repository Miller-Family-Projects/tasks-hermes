from __future__ import annotations

import importlib.util
import sys
from collections.abc import Callable
from pathlib import Path
from types import ModuleType
from typing import TypeAlias

from tasks_hermes.json_types import JsonObject, JsonValue, parse_json_object
from tasks_hermes.plugin import register
from tasks_hermes.schemas import TOOL_SCHEMAS
from tasks_hermes.tools import tasks_create

ToolHandler: TypeAlias = Callable[..., str]

PACKAGE = Path(__file__).resolve().parents[1] / "tasks_hermes"
ROOT = Path(__file__).resolve().parents[1]
EXPECTED_TOOLS = [
    "tasks_create",
    "tasks_list",
    "tasks_update",
    "tasks_note",
    "tasks_complete",
    "tasks_delete",
]


def test_manifest_declares_exact_task_tools() -> None:
    # Given: the Hermes plugin manifest.
    manifest = (PACKAGE / "plugin.yaml").read_text(encoding="utf-8")

    # When: the advertised tool names are inspected.
    advertised = [
        line.strip()[2:] for line in manifest.splitlines() if line.strip().startswith("- ")
    ]

    # Then: only the requested tool names are present.
    assert "name: tasks-hermes" in manifest
    assert advertised == EXPECTED_TOOLS


def test_register_registers_exact_task_tools() -> None:
    # Given: a Hermes-like host that records registered tools.
    class Host:
        def __init__(self) -> None:
            self.names: list[str] = []

        def register_tool(
            self,
            *,
            name: str,
            toolset: str,
            schema: JsonObject,
            handler: ToolHandler,
        ) -> None:
            self.names.append(name)
            assert toolset == "tasks-hermes"
            assert schema["name"] == name
            assert callable(handler)

    host = Host()

    # When: the plugin registers itself.
    register(host)

    # Then: Hermes receives exactly the requested tools.
    assert host.names == EXPECTED_TOOLS


def test_tool_handlers_return_json_strings(tmp_path: Path) -> None:
    # Given: a handler called with a temporary storage path.
    tasks_path = tmp_path / "tasks.json"

    # When: it creates a task.
    result = tasks_create({"title": "Write docs"}, _tasks_path=str(tasks_path))

    # Then: the result is a JSON string.
    payload = parse_json_object(result)
    assert isinstance(result, str)
    assert payload is not None
    assert payload["ok"] is True
    task = json_object(payload["task"])
    assert task["status"] == "pending"


def test_installed_directory_plugin_layout_imports(tmp_path: Path) -> None:
    # Given: package files copied into a flat Hermes directory-plugin layout.
    plugin_dir = tmp_path / "tasks-hermes"
    plugin_dir.mkdir()
    for name in [
        "__init__.py",
        "json_types.py",
        "models.py",
        "plugin.py",
        "plugin.yaml",
        "py.typed",
        "schemas.py",
        "storage.py",
        "tools.py",
    ]:
        _ = (plugin_dir / name).write_text((PACKAGE / name).read_text(encoding="utf-8"))
    spec = importlib.util.spec_from_file_location(
        "tasks_hermes_installed_test",
        plugin_dir / "__init__.py",
        submodule_search_locations=[str(plugin_dir)],
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module

    # When: the directory plugin is imported through its file location.
    spec.loader.exec_module(module)

    # Then: Hermes-visible entry points are available.
    assert isinstance(module, ModuleType)
    assert "register" in dir(module)
    assert "tasks_create" in dir(module)


def test_public_files_do_not_leak_local_operational_data() -> None:
    # Given: files intended for a public repository.
    public_files = [ROOT / "README.md", ROOT / "pyproject.toml", PACKAGE / "plugin.yaml"]

    # When: they are scanned for local-only operational markers.
    combined = "\n".join(path.read_text(encoding="utf-8") for path in public_files)

    # Then: only generic public/plugin data is present.
    assert "/home/limax" not in combined
    assert "Mara" not in combined
    assert "Sona" not in combined
    assert "Matrix" not in combined
    assert "openclaw" not in combined.lower()
    assert set(TOOL_SCHEMAS) == set(EXPECTED_TOOLS)


def json_object(value: JsonValue) -> JsonObject:
    assert isinstance(value, dict)
    return value

from __future__ import annotations

import json
from pathlib import Path
from typing import Final, Literal, TypeAlias

from .json_types import JsonScalar, JsonValue
from .models import Task, TaskId, TaskStatus
from .storage import TaskPatch, TaskStore

ToolArgs: TypeAlias = dict[str, JsonScalar]
ToolResult: TypeAlias = dict[str, JsonValue]
Invalid: TypeAlias = Literal["invalid"]
PATH_KWARG: Final[str] = "_tasks_path"


def tasks_create(args: ToolArgs, **kwargs: JsonScalar) -> str:
    title = required_string(args, "title")
    if title is None:
        return error_json("missing_title", "title is required")
    note = optional_string(args, "note")
    if note is None:
        return error_json("invalid_note", "note must be a string when provided")
    result = store_from_kwargs(kwargs).create(title=title, note=note)
    return task_result_json(result, "task")


def tasks_list(args: ToolArgs, **kwargs: JsonScalar) -> str:
    status = parse_list_status(args.get("status"))
    if status == "invalid":
        return error_json("invalid_status", "status must be pending, in_progress, done, or all")
    result = store_from_kwargs(kwargs).list(status)
    if isinstance(result, str):
        return error_json("storage_error", result)
    return success_json({"tasks": [task.to_json() for task in result.tasks]})


def tasks_update(args: ToolArgs, **kwargs: JsonScalar) -> str:
    task_id = required_string(args, "id")
    if task_id is None:
        return error_json("missing_id", "id is required")
    patch = update_patch(args)
    if isinstance(patch, str):
        return error_json("invalid_update", patch)
    result = store_from_kwargs(kwargs).update(TaskId(task_id), patch)
    return task_result_json(result, "task")


def tasks_note(args: ToolArgs, **kwargs: JsonScalar) -> str:
    task_id = required_string(args, "id")
    note = required_string(args, "note")
    if task_id is None:
        return error_json("missing_id", "id is required")
    if note is None:
        return error_json("missing_note", "note is required")
    result = store_from_kwargs(kwargs).note(TaskId(task_id), note)
    return task_result_json(result, "task")


def tasks_complete(args: ToolArgs, **kwargs: JsonScalar) -> str:
    task_id = required_string(args, "id")
    if task_id is None:
        return error_json("missing_id", "id is required")
    result = store_from_kwargs(kwargs).complete(TaskId(task_id))
    return task_result_json(result, "task")


def tasks_delete(args: ToolArgs, **kwargs: JsonScalar) -> str:
    task_id = required_string(args, "id")
    if task_id is None:
        return error_json("missing_id", "id is required")
    result = store_from_kwargs(kwargs).delete(TaskId(task_id))
    return task_result_json(result, "deleted_task")


def store_from_kwargs(kwargs: ToolArgs) -> TaskStore:
    path = kwargs.get(PATH_KWARG)
    if isinstance(path, str) and path:
        return TaskStore(Path(path))
    return TaskStore()


def required_string(args: ToolArgs, key: str) -> str | None:
    value = args.get(key)
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    if not stripped:
        return None
    return stripped


def optional_string(args: ToolArgs, key: str) -> str | None:
    value = args.get(key)
    if value is None:
        return ""
    if not isinstance(value, str):
        return None
    return value


def parse_list_status(value: JsonScalar) -> TaskStatus | None | Invalid:
    if value is None or value == "all":
        return None
    if not isinstance(value, str):
        return "invalid"
    try:
        return TaskStatus(value)
    except ValueError:
        return "invalid"


def update_patch(args: ToolArgs) -> TaskPatch | str:
    title = optional_patch_string(args, "title")
    if title == "invalid":
        return "title must be a non-empty string when provided"
    status = optional_patch_status(args.get("status"))
    if status == "invalid":
        return "status must be pending, in_progress, or done when provided"
    if title is None and status is None:
        return "provide title or status"
    return TaskPatch(title=title, status=status)


def optional_patch_string(args: ToolArgs, key: str) -> str | None | Invalid:
    value = args.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        return "invalid"
    stripped = value.strip()
    if not stripped:
        return "invalid"
    return stripped


def optional_patch_status(value: JsonScalar) -> TaskStatus | None | Invalid:
    if value is None:
        return None
    if not isinstance(value, str):
        return "invalid"
    try:
        return TaskStatus(value)
    except ValueError:
        return "invalid"


def task_result_json(result: Task | str, key: str) -> str:
    if isinstance(result, str):
        code = "not_found" if result == "task not found" else "storage_error"
        return error_json(code, result)
    return success_json({key: result.to_json()})


def success_json(payload: ToolResult) -> str:
    return json.dumps({"ok": True, **payload}, separators=(",", ":"))


def error_json(code: str, message: str) -> str:
    return json.dumps(
        {"ok": False, "error": {"code": code, "message": message}},
        separators=(",", ":"),
    )

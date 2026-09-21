from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Final, Literal, TypeAlias, cast

from .json_types import JsonScalar, JsonValue
from .models import Task, TaskId, TaskStatus
from .storage import TaskPatch, TaskStore

ToolArgs: TypeAlias = dict[str, JsonScalar]
ToolResult: TypeAlias = dict[str, JsonValue]
Invalid: TypeAlias = Literal["invalid"]
PATH_KWARG: Final[str] = "_tasks_path"
DEFAULT_LIST_LIMIT: Final[int] = 20
MAX_LIST_LIMIT: Final[int] = 100


@dataclass(frozen=True, slots=True)
class ListOptions:
    status: TaskStatus | None
    task_id: str | None
    query: str | None
    limit: int
    offset: int
    include_notes: bool


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
    options = parse_list_options(args)
    if isinstance(options, str):
        return options

    result = store_from_kwargs(kwargs).list(options.status)
    if isinstance(result, str):
        return error_json("storage_error", result)

    tasks = list(result.tasks)
    if options.task_id is not None:
        tasks = [task for task in tasks if task.id == options.task_id]
    if options.query is not None:
        needle = options.query.casefold()
        tasks = [
            task
            for task in tasks
            if needle in task.id.casefold()
            or needle in task.title.casefold()
            or needle in task.note.casefold()
        ]
    tasks.sort(key=lambda task: (task.updated_at, task.created_at, task.id), reverse=True)

    total = len(tasks)
    page = tasks[options.offset : options.offset + options.limit]
    return success_json(
        {
            "tasks": [task_list_json(task, include_notes=options.include_notes) for task in page],
            "count": len(page),
            "total": total,
            "offset": options.offset,
            "limit": options.limit,
            "has_more": options.offset + len(page) < total,
        }
    )


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


def optional_filter_string(args: ToolArgs, key: str) -> tuple[str | None, bool]:
    value = args.get(key)
    if value is None:
        return None, True
    if not isinstance(value, str):
        return None, False
    stripped = value.strip()
    if not stripped:
        return None, False
    return stripped, True


def bounded_integer(value: JsonScalar, *, default: int, minimum: int) -> int | None:
    if value is None:
        return default
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        return None
    return value


def task_list_json(task: Task, *, include_notes: bool) -> ToolResult:
    if include_notes:
        return task.to_json()
    return {
        "id": task.id,
        "title": task.title,
        "status": task.status.value,
        "created_at": task.created_at,
        "updated_at": task.updated_at,
    }


def parse_list_options(args: ToolArgs) -> ListOptions | str:
    status = parse_list_status(args.get("status"))
    task_id, task_id_valid = optional_filter_string(args, "id")
    query, query_valid = optional_filter_string(args, "query")
    limit = bounded_integer(args.get("limit"), default=DEFAULT_LIST_LIMIT, minimum=1)
    offset = bounded_integer(args.get("offset"), default=0, minimum=0)
    include_notes = args.get("include_notes", False)

    error: str | None = None
    if status == "invalid":
        error = error_json(
            "invalid_status",
            "status must be pending, in_progress, done, or all",
        )
    elif not task_id_valid:
        error = error_json("invalid_id", "id must be a non-empty string when provided")
    elif not query_valid:
        error = error_json("invalid_query", "query must be a non-empty string when provided")
    elif limit is None or limit > MAX_LIST_LIMIT:
        error = error_json("invalid_limit", "limit must be an integer from 1 to 100")
    elif offset is None:
        error = error_json("invalid_offset", "offset must be a non-negative integer")
    elif not isinstance(include_notes, bool):
        error = error_json("invalid_include_notes", "include_notes must be a boolean")
    if error is not None:
        return error

    return ListOptions(
        status=cast("TaskStatus | None", status),
        task_id=task_id,
        query=query,
        limit=cast("int", limit),
        offset=cast("int", offset),
        include_notes=cast("bool", include_notes),
    )


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

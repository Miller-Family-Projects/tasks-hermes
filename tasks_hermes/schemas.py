from __future__ import annotations

from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from .json_types import JsonObject

STATUS_DESCRIPTION: Final[str] = "Task status: pending, in_progress, done, or all."
LIST_LIMIT_DESCRIPTION: Final[str] = "Maximum tasks returned (default 20, max 100)."

TASKS_CREATE: Final[JsonObject] = {
    "name": "tasks_create",
    "description": "Create a simple persistent task with an optional note.",
    "parameters": {
        "type": "object",
        "properties": {
            "title": {"type": "string", "description": "Task title."},
            "note": {"type": "string", "description": "Optional task note."},
        },
        "required": ["title"],
    },
}

TASKS_LIST: Final[JsonObject] = {
    "name": "tasks_list",
    "description": (
        "List tasks as compact metadata by default. Supports bounded pagination, exact id, "
        "and text search; notes are returned only when explicitly requested."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "status": {"type": "string", "description": STATUS_DESCRIPTION},
            "id": {"type": "string", "description": "Exact task id."},
            "query": {
                "type": "string",
                "description": "Case-insensitive search across id, title, and note.",
            },
            "limit": {
                "type": "integer",
                "minimum": 1,
                "maximum": 100,
                "description": LIST_LIMIT_DESCRIPTION,
            },
            "offset": {
                "type": "integer",
                "minimum": 0,
                "description": "Tasks to skip after filtering (default 0).",
            },
            "include_notes": {
                "type": "boolean",
                "description": "Return full notes. Defaults to false; enable only deliberately.",
            },
        },
    },
}

TASKS_UPDATE: Final[JsonObject] = {
    "name": "tasks_update",
    "description": "Update a task title and/or status.",
    "parameters": {
        "type": "object",
        "properties": {
            "id": {"type": "string", "description": "Task id."},
            "title": {"type": "string", "description": "New task title."},
            "status": {"type": "string", "description": STATUS_DESCRIPTION},
        },
        "required": ["id"],
    },
}

TASKS_NOTE: Final[JsonObject] = {
    "name": "tasks_note",
    "description": "Add or replace the note on an existing task.",
    "parameters": {
        "type": "object",
        "properties": {
            "id": {"type": "string", "description": "Task id."},
            "note": {"type": "string", "description": "Task note."},
        },
        "required": ["id", "note"],
    },
}

TASKS_COMPLETE: Final[JsonObject] = {
    "name": "tasks_complete",
    "description": "Mark an existing task as done.",
    "parameters": {
        "type": "object",
        "properties": {"id": {"type": "string", "description": "Task id."}},
        "required": ["id"],
    },
}

TASKS_DELETE: Final[JsonObject] = {
    "name": "tasks_delete",
    "description": "Delete an existing task.",
    "parameters": {
        "type": "object",
        "properties": {"id": {"type": "string", "description": "Task id."}},
        "required": ["id"],
    },
}

TOOL_SCHEMAS: Final[dict[str, JsonObject]] = {
    "tasks_create": TASKS_CREATE,
    "tasks_list": TASKS_LIST,
    "tasks_update": TASKS_UPDATE,
    "tasks_note": TASKS_NOTE,
    "tasks_complete": TASKS_COMPLETE,
    "tasks_delete": TASKS_DELETE,
}

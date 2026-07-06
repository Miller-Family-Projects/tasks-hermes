from __future__ import annotations

from collections.abc import Callable
from typing import Protocol, TypeAlias

from .json_types import JsonScalar, JsonValue
from .schemas import TOOL_SCHEMAS
from .tools import (
    tasks_complete,
    tasks_create,
    tasks_delete,
    tasks_list,
    tasks_note,
    tasks_update,
)

ToolArgs: TypeAlias = dict[str, JsonScalar]
ToolHandler: TypeAlias = Callable[..., str]
ToolSchema: TypeAlias = dict[str, JsonValue]


class ToolRegistrar(Protocol):
    def register_tool(
        self,
        *,
        name: str,
        toolset: str,
        schema: ToolSchema,
        handler: ToolHandler,
    ) -> None: ...


TOOL_HANDLERS: dict[str, ToolHandler] = {
    "tasks_create": tasks_create,
    "tasks_list": tasks_list,
    "tasks_update": tasks_update,
    "tasks_note": tasks_note,
    "tasks_complete": tasks_complete,
    "tasks_delete": tasks_delete,
}


def register(ctx: ToolRegistrar) -> None:
    for name, handler in TOOL_HANDLERS.items():
        ctx.register_tool(
            name=name,
            toolset="tasks-hermes",
            schema=TOOL_SCHEMAS[name],
            handler=handler,
        )

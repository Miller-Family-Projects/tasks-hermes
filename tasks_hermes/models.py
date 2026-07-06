from __future__ import annotations

from dataclasses import dataclass, replace
from enum import StrEnum
from typing import NewType, TypeAlias

from .json_types import JsonObject, JsonValue

TaskId = NewType("TaskId", str)


class TaskStatus(StrEnum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    DONE = "done"


TaskJson: TypeAlias = JsonObject
DocumentJson: TypeAlias = JsonObject


@dataclass(frozen=True, slots=True)
class Task:
    id: TaskId
    title: str
    status: TaskStatus
    note: str
    created_at: str
    updated_at: str

    def with_title(self, title: str, updated_at: str) -> Task:
        return replace(self, title=title, updated_at=updated_at)

    def with_status(self, status: TaskStatus, updated_at: str) -> Task:
        return replace(self, status=status, updated_at=updated_at)

    def with_note(self, note: str, updated_at: str) -> Task:
        return replace(self, note=note, updated_at=updated_at)

    def to_json(self) -> TaskJson:
        return {
            "id": self.id,
            "title": self.title,
            "status": self.status.value,
            "note": self.note,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


@dataclass(frozen=True, slots=True)
class TaskDocument:
    tasks: tuple[Task, ...]

    def to_json(self) -> DocumentJson:
        return {"tasks": [task.to_json() for task in self.tasks]}


ParseTaskResult: TypeAlias = Task | str
ParseDocumentResult: TypeAlias = TaskDocument | str


def parse_status(value: JsonValue) -> TaskStatus | None:
    if not isinstance(value, str):
        return None
    try:
        return TaskStatus(value)
    except ValueError:
        return None


def parse_task(value: JsonValue) -> ParseTaskResult:
    if not isinstance(value, dict):
        return "task must be an object"
    id_value = value.get("id")
    title = value.get("title")
    status = parse_status(value.get("status"))
    note = value.get("note")
    created_at = value.get("created_at")
    updated_at = value.get("updated_at")
    error: str | None = None
    if not isinstance(id_value, str) or not id_value:
        error = "task.id must be a non-empty string"
    elif not isinstance(title, str) or not title:
        error = "task.title must be a non-empty string"
    elif status is None:
        error = "task.status must be pending, in_progress, or done"
    elif not isinstance(note, str):
        error = "task.note must be a string"
    elif not isinstance(created_at, str) or not created_at:
        error = "task.created_at must be a non-empty string"
    elif not isinstance(updated_at, str) or not updated_at:
        error = "task.updated_at must be a non-empty string"
    if error is not None:
        return error
    if (
        isinstance(id_value, str)
        and isinstance(title, str)
        and status is not None
        and isinstance(note, str)
        and isinstance(created_at, str)
        and isinstance(updated_at, str)
    ):
        return Task(
            id=TaskId(id_value),
            title=title,
            status=status,
            note=note,
            created_at=created_at,
            updated_at=updated_at,
        )
    return "task is invalid"


def parse_document(value: JsonValue) -> ParseDocumentResult:
    if not isinstance(value, dict):
        return "document must be an object"
    tasks = value.get("tasks")
    if not isinstance(tasks, list):
        return "document.tasks must be a list"
    parsed_tasks: list[Task] = []
    for task_value in tasks:
        task = parse_task(task_value)
        if isinstance(task, str):
            return task
        parsed_tasks.append(task)
    return TaskDocument(tuple(parsed_tasks))

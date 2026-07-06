from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Final, TypeAlias
from uuid import uuid4

from .json_types import parse_json
from .models import Task, TaskDocument, TaskId, TaskStatus, parse_document

DEFAULT_TASKS_PATH: Final[Path] = Path("/opt/data/workspace/tasks.json")
TEMP_SUFFIX: Final[str] = ".tmp"
ID_HEX_CHARS: Final[int] = 12

StoreResult: TypeAlias = TaskDocument | str
TaskResult: TypeAlias = Task | str


@dataclass(frozen=True, slots=True)
class TaskPatch:
    title: str | None
    status: TaskStatus | None


@dataclass(frozen=True, slots=True)
class TaskStore:
    path: Path = DEFAULT_TASKS_PATH

    def create(self, title: str, note: str) -> TaskResult:
        document = self.load()
        if isinstance(document, str):
            return document
        now = timestamp_now()
        task = Task(
            id=new_task_id(),
            title=title,
            status=TaskStatus.PENDING,
            note=note,
            created_at=now,
            updated_at=now,
        )
        self.save(TaskDocument((*document.tasks, task)))
        return task

    def list(self, status: TaskStatus | None) -> StoreResult:
        document = self.load()
        if isinstance(document, str):
            return document
        if status is None:
            return document
        return TaskDocument(tuple(task for task in document.tasks if task.status == status))

    def update(self, task_id: TaskId, patch: TaskPatch) -> TaskResult:
        document = self.load()
        if isinstance(document, str):
            return document
        task = find_task(document.tasks, task_id)
        if task is None:
            return "task not found"
        updated = apply_patch(task, patch, timestamp_now())
        self.save(replace_task(document, updated))
        return updated

    def note(self, task_id: TaskId, note: str) -> TaskResult:
        document = self.load()
        if isinstance(document, str):
            return document
        task = find_task(document.tasks, task_id)
        if task is None:
            return "task not found"
        updated = task.with_note(note, timestamp_now())
        self.save(replace_task(document, updated))
        return updated

    def complete(self, task_id: TaskId) -> TaskResult:
        return self.update(task_id, TaskPatch(title=None, status=TaskStatus.DONE))

    def delete(self, task_id: TaskId) -> TaskResult:
        document = self.load()
        if isinstance(document, str):
            return document
        task = find_task(document.tasks, task_id)
        if task is None:
            return "task not found"
        self.save(TaskDocument(tuple(item for item in document.tasks if item.id != task_id)))
        return task

    def load(self) -> StoreResult:
        if not self.path.exists():
            return TaskDocument(())
        try:
            text = self.path.read_text(encoding="utf-8")
        except OSError as exc:
            return f"could not read tasks file: {exc}"
        value = parse_json(text)
        if value is None:
            return "tasks file is not valid JSON"
        return parse_document(value)

    def save(self, document: TaskDocument) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = self.path.with_name(f"{self.path.name}{TEMP_SUFFIX}")
        _ = temp_path.write_text(
            json.dumps(document.to_json(), indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        _ = temp_path.replace(self.path)


def timestamp_now() -> str:
    return datetime.now(UTC).replace(tzinfo=None).isoformat(timespec="seconds")


def new_task_id() -> TaskId:
    return TaskId(f"task_{uuid4().hex[:ID_HEX_CHARS]}")


def find_task(tasks: tuple[Task, ...], task_id: TaskId) -> Task | None:
    for task in tasks:
        if task.id == task_id:
            return task
    return None


def apply_patch(task: Task, patch: TaskPatch, updated_at: str) -> Task:
    updated = task
    if patch.title is not None:
        updated = updated.with_title(patch.title, updated_at)
    if patch.status is not None:
        updated = updated.with_status(patch.status, updated_at)
    return updated


def replace_task(document: TaskDocument, task: Task) -> TaskDocument:
    return TaskDocument(tuple(task if item.id == task.id else item for item in document.tasks))

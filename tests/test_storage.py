from __future__ import annotations

from pathlib import Path

from tasks_hermes.models import TaskDocument, TaskId, TaskStatus
from tasks_hermes.storage import DEFAULT_TASKS_PATH, TaskPatch, TaskStore


def test_default_path_matches_hermes_workspace_contract() -> None:
    # Given: the plugin storage contract.
    expected = Path("/opt/data/workspace/tasks.json")

    # When: the default path is inspected.
    actual = DEFAULT_TASKS_PATH

    # Then: it matches the requested Hermes workspace file.
    assert actual == expected


def test_missing_file_loads_empty_document(tmp_path: Path) -> None:
    # Given: a store path that does not exist.
    store = TaskStore(tmp_path / "tasks.json")

    # When: the document is loaded.
    result = store.load()

    # Then: the store starts empty without touching the default path.
    assert result == TaskDocument(())


def test_create_persists_task_with_note(tmp_path: Path) -> None:
    # Given: an empty task store.
    store = TaskStore(tmp_path / "tasks.json")

    # When: a task is created.
    created = store.create("Compare models", "Krea2 works")

    # Then: it can be loaded from disk with the requested fields.
    assert not isinstance(created, str)
    loaded = store.load()
    assert not isinstance(loaded, str)
    task = loaded.tasks[0]
    assert task.id == created.id
    assert task.title == "Compare models"
    assert task.status == TaskStatus.PENDING
    assert task.note == "Krea2 works"


def test_update_changes_title_and_status(tmp_path: Path) -> None:
    # Given: a persisted task.
    store = TaskStore(tmp_path / "tasks.json")
    created = store.create("Draft", "")
    assert not isinstance(created, str)

    # When: title and status are updated.
    updated = store.update(
        created.id,
        TaskPatch(title="Draft docs", status=TaskStatus.IN_PROGRESS),
    )

    # Then: the returned task has the new values.
    assert not isinstance(updated, str)
    assert updated.title == "Draft docs"
    assert updated.status == TaskStatus.IN_PROGRESS


def test_delete_removes_task_from_document(tmp_path: Path) -> None:
    # Given: a persisted task.
    store = TaskStore(tmp_path / "tasks.json")
    created = store.create("Remove me", "")
    assert not isinstance(created, str)

    # When: it is deleted.
    deleted = store.delete(created.id)

    # Then: the deleted task is returned and the document is empty.
    assert deleted == created
    loaded = store.load()
    assert loaded == TaskDocument(())


def test_malformed_file_returns_storage_error(tmp_path: Path) -> None:
    # Given: a malformed JSON storage file.
    path = tmp_path / "tasks.json"
    _ = path.write_text("not-json", encoding="utf-8")

    # When: the document is loaded.
    result = TaskStore(path).load()

    # Then: the error is returned as data for tool serialization.
    assert result == "tasks file is not valid JSON"


def test_unknown_delete_returns_not_found(tmp_path: Path) -> None:
    # Given: an empty store.
    store = TaskStore(tmp_path / "tasks.json")

    # When: an unknown id is deleted.
    result = store.delete(TaskId("task_missing"))

    # Then: the operation reports a task-level error.
    assert result == "task not found"

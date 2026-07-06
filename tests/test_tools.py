from __future__ import annotations

from typing import TYPE_CHECKING

from tasks_hermes.json_types import JsonObject, JsonValue, parse_json_object
from tasks_hermes.tools import (
    tasks_complete,
    tasks_create,
    tasks_delete,
    tasks_list,
    tasks_note,
    tasks_update,
)

if TYPE_CHECKING:
    from pathlib import Path


def parse_result(result: str) -> JsonObject:
    value = parse_json_object(result)
    assert value is not None
    return value


def json_object(value: JsonValue) -> JsonObject:
    assert isinstance(value, dict)
    return value


def json_list(value: JsonValue) -> list[JsonValue]:
    assert isinstance(value, list)
    return value


def json_string(value: JsonValue) -> str:
    assert isinstance(value, str)
    return value


def test_tasks_create_returns_task_with_required_fields(tmp_path: Path) -> None:
    # Given: a temporary tasks file.
    path = tmp_path / "tasks.json"

    # When: a task is created with a note.
    payload = parse_result(
        tasks_create({"title": "Compare models", "note": "Krea2 works"}, _tasks_path=str(path)),
    )

    # Then: the response contains the created task.
    task = json_object(payload["task"])
    assert payload["ok"] is True
    assert json_string(task["id"]).startswith("task_")
    assert task["title"] == "Compare models"
    assert task["status"] == "pending"
    assert task["note"] == "Krea2 works"
    assert isinstance(task["created_at"], str)
    assert isinstance(task["updated_at"], str)


def test_tasks_list_filters_by_status(tmp_path: Path) -> None:
    # Given: pending and done tasks.
    path = tmp_path / "tasks.json"
    pending = json_object(
        parse_result(tasks_create({"title": "Pending"}, _tasks_path=str(path)))["task"]
    )
    done = json_object(parse_result(tasks_create({"title": "Done"}, _tasks_path=str(path)))["task"])
    done_id = json_string(done["id"])
    _ = tasks_complete({"id": done_id}, _tasks_path=str(path))

    # When: pending tasks are listed.
    payload = parse_result(tasks_list({"status": "pending"}, _tasks_path=str(path)))

    # Then: only pending tasks are returned.
    assert payload["ok"] is True
    tasks = [json_object(task) for task in json_list(payload["tasks"])]
    assert [task["id"] for task in tasks] == [json_string(pending["id"])]


def test_tasks_update_changes_title_and_status(tmp_path: Path) -> None:
    # Given: a task.
    path = tmp_path / "tasks.json"
    task = json_object(parse_result(tasks_create({"title": "Old"}, _tasks_path=str(path)))["task"])

    # When: it is updated.
    payload = parse_result(
        tasks_update(
            {"id": json_string(task["id"]), "title": "New", "status": "in_progress"},
            _tasks_path=str(path),
        ),
    )

    # Then: the updated task is returned.
    updated = json_object(payload["task"])
    assert updated["title"] == "New"
    assert updated["status"] == "in_progress"


def test_tasks_note_replaces_note(tmp_path: Path) -> None:
    # Given: a task with an initial note.
    path = tmp_path / "tasks.json"
    task = json_object(
        parse_result(tasks_create({"title": "Task", "note": "old"}, _tasks_path=str(path)))["task"],
    )

    # When: its note is replaced.
    payload = parse_result(
        tasks_note({"id": json_string(task["id"]), "note": "new"}, _tasks_path=str(path))
    )

    # Then: the new note is returned.
    updated = json_object(payload["task"])
    assert updated["note"] == "new"


def test_tasks_complete_marks_done(tmp_path: Path) -> None:
    # Given: a pending task.
    path = tmp_path / "tasks.json"
    task = json_object(parse_result(tasks_create({"title": "Task"}, _tasks_path=str(path)))["task"])

    # When: it is completed.
    payload = parse_result(tasks_complete({"id": json_string(task["id"])}, _tasks_path=str(path)))

    # Then: the status is done.
    completed = json_object(payload["task"])
    assert completed["status"] == "done"


def test_tasks_delete_returns_confirmation(tmp_path: Path) -> None:
    # Given: a task.
    path = tmp_path / "tasks.json"
    task = json_object(
        parse_result(tasks_create({"title": "Delete"}, _tasks_path=str(path)))["task"]
    )

    # When: it is deleted.
    task_id = json_string(task["id"])
    payload = parse_result(tasks_delete({"id": task_id}, _tasks_path=str(path)))

    # Then: the deleted task is returned as confirmation.
    assert payload["ok"] is True
    deleted = json_object(payload["deleted_task"])
    assert deleted["id"] == task_id
    assert json_list(parse_result(tasks_list({}, _tasks_path=str(path)))["tasks"]) == []


def test_unknown_task_returns_json_error(tmp_path: Path) -> None:
    # Given: an empty tasks file.
    path = tmp_path / "tasks.json"

    # When: an unknown task is completed.
    payload = parse_result(tasks_complete({"id": "task_missing"}, _tasks_path=str(path)))

    # Then: the error is serialized as JSON.
    assert payload == {
        "ok": False,
        "error": {"code": "not_found", "message": "task not found"},
    }


def test_invalid_status_returns_json_error(tmp_path: Path) -> None:
    # Given: a temporary tasks file.
    path = tmp_path / "tasks.json"

    # When: the list status is invalid.
    payload = parse_result(tasks_list({"status": "blocked"}, _tasks_path=str(path)))

    # Then: the handler reports the accepted status values.
    assert payload["ok"] is False
    error = json_object(payload["error"])
    assert error["code"] == "invalid_status"

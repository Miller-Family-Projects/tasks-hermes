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


def test_tasks_list_is_compact_and_bounded_by_default(tmp_path: Path) -> None:
    # Given: more tasks than the default page size, each with a large note.
    path = tmp_path / "tasks.json"
    for index in range(25):
        _ = tasks_create(
            {"title": f"Task {index}", "note": f"note-{index}-" + ("x" * 2_000)},
            _tasks_path=str(path),
        )

    # When: tasks are listed without requesting notes or pagination.
    payload = parse_result(tasks_list({}, _tasks_path=str(path)))

    # Then: the response is bounded and notes are omitted.
    tasks = [json_object(task) for task in json_list(payload["tasks"])]
    assert payload["count"] == 20
    assert payload["total"] == 25
    assert payload["has_more"] is True
    assert payload["limit"] == 20
    assert len(tasks) == 20
    assert all("note" not in task for task in tasks)


def test_tasks_list_searches_notes_without_emitting_them(tmp_path: Path) -> None:
    # Given: one task whose note contains the search term.
    path = tmp_path / "tasks.json"
    matching = json_object(
        parse_result(
            tasks_create(
                {"title": "Architecture study", "note": "contains-needle-but-is-private"},
                _tasks_path=str(path),
            )
        )["task"]
    )
    _ = tasks_create({"title": "Other", "note": "unrelated"}, _tasks_path=str(path))

    # When: list is filtered by a query found only in the note.
    payload = parse_result(tasks_list({"query": "needle"}, _tasks_path=str(path)))

    # Then: only compact task metadata is returned.
    tasks = [json_object(task) for task in json_list(payload["tasks"])]
    assert payload["total"] == 1
    assert [task["id"] for task in tasks] == [matching["id"]]
    assert "note" not in tasks[0]


def test_tasks_list_exact_id_can_explicitly_include_note(tmp_path: Path) -> None:
    # Given: a task with a note.
    path = tmp_path / "tasks.json"
    created = json_object(
        parse_result(
            tasks_create({"title": "Target", "note": "full detail"}, _tasks_path=str(path))
        )["task"]
    )

    # When: the exact task is requested with notes explicitly enabled.
    payload = parse_result(
        tasks_list(
            {"id": json_string(created["id"]), "include_notes": True},
            _tasks_path=str(path),
        )
    )

    # Then: exactly that full task is returned.
    tasks = [json_object(task) for task in json_list(payload["tasks"])]
    assert payload["total"] == 1
    assert tasks == [created]


def test_tasks_list_rejects_unbounded_limit(tmp_path: Path) -> None:
    # Given: a temporary tasks file.
    path = tmp_path / "tasks.json"

    # When: the caller asks for more than the hard maximum.
    payload = parse_result(tasks_list({"limit": 101}, _tasks_path=str(path)))

    # Then: the handler refuses the unbounded request.
    assert payload == {
        "ok": False,
        "error": {"code": "invalid_limit", "message": "limit must be an integer from 1 to 100"},
    }


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

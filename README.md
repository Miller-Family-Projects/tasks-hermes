# tasks-hermes

`tasks-hermes` is a small Hermes directory plugin for persistent tasks with one
editable note per task.

The plugin is intentionally runtime-agnostic. It does not assume a specific host,
workspace, identity, chat bridge, or deployment layout.

## Status

This is an alpha plugin for Hermes runtimes that support Python directory
plugins with registered tools. It is packaged as normal Python code and can also
be copied into Hermes' directory-plugin layout.

## Behavior

- Stores tasks in JSON at `/opt/data/workspace/tasks.json` by default.
- Uses a minimal document shape: `{ "tasks": [...] }`.
- Supports the statuses `pending`, `in_progress`, and `done`.
- Keeps one note string on each task.
- Creates the storage parent directory when saving for the first time.
- Uses an atomic temporary-file replace when writing the JSON document.
- Returns JSON strings from every Hermes tool handler, including errors.

Example storage file:

```json
{
  "tasks": [
    {
      "id": "task_8f4f1d2a9c31",
      "title": "Compare model hosts",
      "status": "pending",
      "note": "Krea2 works. Others not tested.",
      "created_at": "2026-07-06T13:00:00",
      "updated_at": "2026-07-06T13:00:00"
    }
  ]
}
```

## Tools

### `tasks_create`

Arguments:

```json
{ "title": "Write release notes", "note": "Mention storage path." }
```

Returns:

```json
{ "ok": true, "task": { "id": "task_...", "status": "pending" } }
```

### `tasks_list`

Arguments:

```json
{ "status": "pending", "query": "agent executor", "limit": 10 }
```

`status` is optional and defaults to `all`. Accepted values are `pending`,
`in_progress`, `done`, and `all`. Results are compact and bounded by default:

- notes are omitted unless `include_notes` is explicitly `true`;
- `limit` defaults to 20 and cannot exceed 100;
- `offset` provides pagination;
- `id` selects an exact task;
- `query` searches task id, title, and note without emitting the note.

Use `include_notes: true` only when the note content is required, preferably
together with an exact `id` or a narrow query.

Returns:

```json
{
  "ok": true,
  "tasks": [],
  "count": 0,
  "total": 0,
  "offset": 0,
  "limit": 20,
  "has_more": false
}
```

### `tasks_update`

Arguments:

```json
{ "id": "task_...", "title": "New title", "status": "in_progress" }
```

`title` and `status` are optional, but at least one must be provided.

### `tasks_note`

Arguments:

```json
{ "id": "task_...", "note": "Updated note." }
```

Adds or replaces the note string on the task.

### `tasks_complete`

Arguments:

```json
{ "id": "task_..." }
```

Marks the task as `done`.

### `tasks_delete`

Arguments:

```json
{ "id": "task_..." }
```

Deletes the task and returns the deleted task as confirmation.

## Install

For package-based use:

```bash
uv add tasks-hermes
```

For direct source installs while testing:

```bash
uv pip install .
```

## Hermes Plugin Layout

Install the plugin directory so Hermes can discover it as:

```text
$HERMES_HOME/plugins/tasks-hermes/
  __init__.py
  json_types.py
  models.py
  plugin.py
  plugin.yaml
  py.typed
  schemas.py
  storage.py
  tools.py
```

Activation is controlled by Hermes configuration, for example by adding the
plugin name to `plugins.enabled` in the target Hermes profile.

## Validate

Run the local checks with `uv`:

```bash
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run basedpyright
```

Build the Python package artifacts with:

```bash
uv build
```

The standalone repository also includes a GitHub Actions workflow that runs the
same checks on Python 3.11, 3.12, and 3.13.

## Non-Goals

- This package does not edit Hermes config.
- This package does not enable itself in any running profile.
- This package does not restart, recreate, or otherwise manage a Hermes runtime.
- This package does not use a database.
- This package does not implement Kanban boards, projects, tags, or recurrence.

Deployment wrappers should keep activation as a separate operator decision.

## License

MIT. See `LICENSE`.

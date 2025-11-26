# GPT Test Task Manager

A lightweight command-line tool for tracking tasks in a local JSON file. Add, list, complete, delete, and clear tasks without any external dependencies.

## Usage

```bash
python -m task_app.cli --help
```

Create a task:

```bash
python -m task_app.cli add "Write documentation" --description "Summarize the new CLI"
```

List tasks:

```bash
python -m task_app.cli list
python -m task_app.cli list --completed
python -m task_app.cli list --open
```

Complete a task and remove it:

```bash
python -m task_app.cli complete 1
python -m task_app.cli delete 1
```

Clear everything:

```bash
python -m task_app.cli clear
```

Use a custom storage location if desired:

```bash
python -m task_app.cli --storage data/tasks.json list
```

## Notes

- Task identifiers are assigned incrementally and preserved across runs via the storage file.
- The tool avoids single-letter names for clarity, following the project request.
- No third-party packages are required; it runs on the Python standard library.

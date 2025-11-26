import argparse
from pathlib import Path
from typing import Optional

from .models import Task
from .storage import Storage


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Lightweight task list manager")
    parser.add_argument(
        "--storage", type=Path, default=Path("tasks.json"), help="Path to tasks storage JSON file"
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    add_parser = subparsers.add_parser("add", help="Add a new task")
    add_parser.add_argument("title", help="Short title for the task")
    add_parser.add_argument("--description", default="", help="Optional task description")

    list_parser = subparsers.add_parser("list", help="List tasks")
    completion_group = list_parser.add_mutually_exclusive_group()
    completion_group.add_argument("--completed", action="store_true", help="Show only completed tasks")
    completion_group.add_argument("--open", action="store_true", help="Show only open tasks")

    complete_parser = subparsers.add_parser("complete", help="Mark a task as complete")
    complete_parser.add_argument("identifier", type=int, help="Identifier of the task to mark complete")

    delete_parser = subparsers.add_parser("delete", help="Remove a task")
    delete_parser.add_argument("identifier", type=int, help="Identifier of the task to delete")

    subparsers.add_parser("clear", help="Remove all tasks")

    return parser


def display_task(task: Task) -> str:
    status = "✓" if task.completed else "•"
    description = f" - {task.description}" if task.description else ""
    return f"[{status}] {task.identifier}: {task.title}{description} (created {task.created_at})"


def handle_add(storage: Storage, title: str, description: str) -> None:
    manager = storage.load()
    new_task = manager.add_task(title=title, description=description)
    storage.save(manager)
    print(f"Created task {new_task.identifier}: {new_task.title}")


def handle_list(storage: Storage, show_completed: Optional[bool]) -> None:
    manager = storage.load()
    filtered_tasks = manager.list_tasks(show_completed=show_completed)
    if not filtered_tasks:
        print("No tasks found.")
        return
    for task in filtered_tasks:
        print(display_task(task))


def handle_complete(storage: Storage, identifier: int) -> None:
    manager = storage.load()
    updated_task = manager.mark_complete(identifier)
    storage.save(manager)
    print(f"Marked task {updated_task.identifier} as complete")


def handle_delete(storage: Storage, identifier: int) -> None:
    manager = storage.load()
    removed_task = manager.delete_task(identifier)
    storage.save(manager)
    print(f"Deleted task {removed_task.identifier}: {removed_task.title}")


def handle_clear(storage: Storage) -> None:
    manager = storage.load()
    manager.clear_tasks()
    storage.save(manager)
    print("All tasks cleared.")


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    storage = Storage(storage_path=args.storage)

    if args.command == "add":
        handle_add(storage, title=args.title, description=args.description)
    elif args.command == "list":
        completion_filter: Optional[bool]
        if args.completed:
            completion_filter = True
        elif args.open:
            completion_filter = False
        else:
            completion_filter = None
        handle_list(storage, show_completed=completion_filter)
    elif args.command == "complete":
        handle_complete(storage, identifier=args.identifier)
    elif args.command == "delete":
        handle_delete(storage, identifier=args.identifier)
    elif args.command == "clear":
        handle_clear(storage)


if __name__ == "__main__":
    main()

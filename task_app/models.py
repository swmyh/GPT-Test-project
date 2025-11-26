from dataclasses import dataclass, field
from datetime import datetime
from typing import List


def current_timestamp() -> str:
    """Return the current UTC timestamp as an ISO formatted string."""
    return datetime.utcnow().isoformat() + "Z"


@dataclass
class Task:
    identifier: int
    title: str
    description: str = ""
    completed: bool = False
    created_at: str = field(default_factory=current_timestamp)

    def to_dict(self) -> dict:
        return {
            "identifier": self.identifier,
            "title": self.title,
            "description": self.description,
            "completed": self.completed,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Task":
        return cls(
            identifier=data["identifier"],
            title=data["title"],
            description=data.get("description", ""),
            completed=data.get("completed", False),
            created_at=data.get("created_at", current_timestamp()),
        )


class TaskManager:
    def __init__(self, tasks: List[Task] | None = None) -> None:
        self.tasks: List[Task] = tasks or []

    def add_task(self, title: str, description: str = "") -> Task:
        next_identifier = 1 if not self.tasks else max(task.identifier for task in self.tasks) + 1
        new_task = Task(identifier=next_identifier, title=title, description=description)
        self.tasks.append(new_task)
        return new_task

    def list_tasks(self, show_completed: bool | None = None) -> List[Task]:
        if show_completed is None:
            return list(self.tasks)
        return [task for task in self.tasks if task.completed is show_completed]

    def mark_complete(self, identifier: int) -> Task:
        task = self._find_task(identifier)
        task.completed = True
        return task

    def delete_task(self, identifier: int) -> Task:
        task = self._find_task(identifier)
        self.tasks = [existing for existing in self.tasks if existing.identifier != identifier]
        return task

    def clear_tasks(self) -> None:
        self.tasks.clear()

    def _find_task(self, identifier: int) -> Task:
        for task in self.tasks:
            if task.identifier == identifier:
                return task
        raise ValueError(f"Task with id {identifier} not found")

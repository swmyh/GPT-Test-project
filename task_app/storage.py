import json
from pathlib import Path
from typing import List

from .models import Task, TaskManager


class Storage:
    def __init__(self, storage_path: Path) -> None:
        self.storage_path = storage_path

    def load(self) -> TaskManager:
        if not self.storage_path.exists():
            return TaskManager()

        with self.storage_path.open("r", encoding="utf-8") as file_handle:
            raw_tasks = json.load(file_handle)

        tasks: List[Task] = [Task.from_dict(item) for item in raw_tasks]
        return TaskManager(tasks=tasks)

    def save(self, manager: TaskManager) -> None:
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        with self.storage_path.open("w", encoding="utf-8") as file_handle:
            json.dump([task.to_dict() for task in manager.tasks], file_handle, indent=2)

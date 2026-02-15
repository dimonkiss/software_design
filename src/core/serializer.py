import json
import dataclasses
from src.core.models import Project, ThreadModel, Block


class ProjectSerializer:
    @staticmethod
    def serialize(project: Project) -> str:
        """Перетворює об'єкт Project у форматований JSON-рядок."""
        data = dataclasses.asdict(project)
        return json.dumps(data, indent=4, ensure_ascii=False)

    @staticmethod
    def deserialize(json_str: str) -> Project:
        """Відновлює об'єкт Project із JSON-рядка."""
        try:
            data = json.loads(json_str)
        except json.JSONDecodeError as e:
            raise ValueError(f"Некоректний JSON файл: {e}")

        threads = []
        for t_data in data.get('threads', []):
            blocks = []
            for b_data in t_data.get('blocks', []):
                blocks.append(Block(**b_data))

            threads.append(ThreadModel(
                id=t_data['id'],
                name=t_data['name'],
                blocks=blocks
            ))

        return Project(
            name=data.get('name', 'New Project'),
            threads=threads,
            shared_variables=data.get('shared_variables', [])
        )
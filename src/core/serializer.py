import json
import dataclasses
from models import Project, ThreadModel, Block


class ProjectSerializer:
    @staticmethod
    def serialize(project: Project) -> str:
        """Перетворює об'єкт проекту в JSON рядок."""
        return json.dumps(dataclasses.asdict(project), indent=4)

    @staticmethod
    def deserialize(data_str: str) -> Project:
        """Відновлює об'єкт проекту з JSON рядка."""
        data = json.loads(data_str)

        threads = []
        for t_data in data.get('threads', []):
            blocks = [Block(**b_data) for b_data in t_data.get('blocks', [])]
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
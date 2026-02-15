import json
from src.core.models import Block
from src.core.serializer import ProjectSerializer


def test_block_creation():
    """Перевірка створення блоку з правильними параметрами."""
    b = Block(id=1, type="ASSIGN", target_var="var1", value=100)
    assert b.id == 1
    assert b.type == "ASSIGN"
    assert b.value == 100


def test_serialization(simple_valid_project):
    """Перевірка: об'єкт -> JSON -> об'єкт."""
    # 1. Serialize
    json_str = ProjectSerializer.serialize(simple_valid_project)

    # Перевіряємо, що це валідний JSON
    data = json.loads(json_str)
    assert data['name'] == "Valid Project"
    assert len(data['threads']) == 1

    # 2. Deserialize
    restored_project = ProjectSerializer.deserialize(json_str)

    # Перевіряємо рівність даних
    assert restored_project.name == simple_valid_project.name
    assert len(restored_project.threads) == 1
    assert restored_project.threads[0].blocks[1].type == "ASSIGN"
    assert restored_project.threads[0].blocks[1].value == 10
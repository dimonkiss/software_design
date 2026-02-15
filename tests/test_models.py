import json
import pytest
from src.core.models import Block, ThreadModel, Project
from src.core.serializer import ProjectSerializer


def test_create_block_defaults():
    """Перевірка значень за замовчуванням."""
    b = Block(id=1, type="START")
    assert b.next_id is None
    assert b.value is None
    assert b.target_var is None


def test_full_serialization_cycle():
    """Складний тест: Проект -> JSON -> Проект."""
    proj = Project(name="Complex Project", shared_variables=["var0", "var99"])

    # Створюємо потік
    t1 = ThreadModel(id=1, name="Main Thread")
    b1 = Block(id=1, type="START", next_id=2, pos_x=10, pos_y=10)
    b2 = Block(id=2, type="ASSIGN", target_var="var0", value=12345, next_id=3)
    b3 = Block(id=3, type="DECISION", target_var="var0", operator="<", value=100, true_next_id=4, false_next_id=5)
    b4 = Block(id=4, type="END")
    b5 = Block(id=5, type="PRINT", target_var="var0", next_id=4)

    t1.blocks = [b1, b2, b3, b4, b5]
    proj.threads.append(t1)

    # 1. Серіалізація
    json_str = ProjectSerializer.serialize(proj)
    data = json.loads(json_str)

    assert data["threads"][0]["blocks"][2]["type"] == "DECISION"
    assert data["threads"][0]["blocks"][1]["value"] == 12345

    # 2. Десеріалізація
    new_proj = ProjectSerializer.deserialize(json_str)

    assert len(new_proj.threads) == 1
    restored_t = new_proj.threads[0]
    assert len(restored_t.blocks) == 5
    # Перевіряємо Decision блок
    decision_block = next(b for b in restored_t.blocks if b.type == "DECISION")
    assert decision_block.operator == "<"
    assert decision_block.true_next_id == 4
    assert decision_block.false_next_id == 5


def test_deserialize_malformed_json():
    """Спроба завантажити битий файл."""
    bad_json = "{ 'name': 'Broken "
    with pytest.raises(ValueError):
        ProjectSerializer.deserialize(bad_json)
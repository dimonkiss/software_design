import pytest
from src.core.models import Project, ThreadModel, Block


@pytest.fixture
def empty_project():
    return Project(name="Test Project")


@pytest.fixture
def simple_valid_project():
    """Створює проект з 1 потоком: START -> ASSIGN -> END"""
    proj = Project(name="Valid Project")

    t1 = ThreadModel(id=1, name="Thread 1")

    b1 = Block(id=1, type="START", next_id=2)
    b2 = Block(id=2, type="ASSIGN", target_var="var0", value=10, next_id=3)
    b3 = Block(id=3, type="END")

    t1.blocks = [b1, b2, b3]
    proj.threads.append(t1)
    return proj
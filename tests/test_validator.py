import pytest
from src.core.models import Project, ThreadModel, Block, MAX_VAL
from src.core.validator import ProjectValidator


@pytest.fixture
def base_project():
    return Project()


def test_validate_no_threads(base_project):
    """Помилка: 0 потоків."""
    valid, errors = ProjectValidator.validate(base_project)
    assert not valid
    assert "1-100 threads" in str(errors[0])


def test_validate_missing_start_end(base_project):
    """Помилка: немає START або END."""
    t = ThreadModel(id=1, name="Bad Thread")
    t.blocks.append(Block(id=1, type="ASSIGN"))
    base_project.threads.append(t)

    valid, errors = ProjectValidator.validate(base_project)
    assert not valid
    error_msgs = [str(e) for e in errors]
    assert any("exactly 1 START" in msg for msg in error_msgs)
    assert any("at least 1 END" in msg for msg in error_msgs)


def test_validate_broken_link(base_project):
    """Помилка: посилання на неіснуючий блок."""
    t = ThreadModel(id=1, name="Broken Link Thread")  # <--- Додано name

    t.blocks.append(Block(id=1, type="START", next_id=99))
    t.blocks.append(Block(id=2, type="END"))
    base_project.threads.append(t)

    valid, errors = ProjectValidator.validate(base_project)
    assert not valid
    assert any("non-existent next block (ID: 99)" in str(e) for e in errors)


def test_validate_value_overflow(base_project):
    """Помилка: число більше за 2^31-1."""
    t = ThreadModel(id=1, name="Overflow Thread")  # <--- Додано name
    t.blocks.append(Block(id=1, type="START", next_id=2))

    bad_val = MAX_VAL + 1
    t.blocks.append(Block(id=2, type="ASSIGN", value=bad_val, next_id=3))
    t.blocks.append(Block(id=3, type="END"))
    base_project.threads.append(t)

    valid, errors = ProjectValidator.validate(base_project)
    assert not valid
    assert any("out of 32-bit" in str(e) for e in errors)


def test_validate_max_blocks_limit(base_project):
    """Помилка: 101 блок у потоці."""
    t = ThreadModel(id=1, name="Huge Thread")  # <--- Додано name

    # Створюємо 101 блок
    for i in range(1, 102):
        t.blocks.append(Block(id=i, type="ASSIGN"))

    base_project.threads.append(t)

    errors = ProjectValidator._validate_thread(t, [])
    assert any("exceeds 100 blocks" in str(e) for e in errors)
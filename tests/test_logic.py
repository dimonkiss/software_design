from src.core.validator import ProjectValidator
from src.core.engine.generator import PythonGenerator
from src.core.models import Block, ThreadModel


def test_validator_success(simple_valid_project):
    """Валідний проект має проходити перевірку."""
    is_valid, errors = ProjectValidator.validate(simple_valid_project)
    assert is_valid is True
    assert len(errors) == 0


def test_validator_empty_thread(empty_project):
    """Порожній потік має викликати помилку."""
    t1 = ThreadModel(id=1, name="Empty")
    empty_project.threads.append(t1)

    is_valid, errors = ProjectValidator.validate(empty_project)
    assert is_valid is False
    assert any("Thread is empty" in str(e) for e in errors)


def test_validator_missing_start(empty_project):
    """Потік без START має бути невалідним."""
    t1 = ThreadModel(id=1, name="No Start")
    # Тільки END
    t1.blocks.append(Block(id=1, type="END"))
    empty_project.threads.append(t1)

    is_valid, errors = ProjectValidator.validate(empty_project)
    assert is_valid is False
    assert any("must have exactly 1 START" in str(e) for e in errors)


def test_validator_overflow(empty_project):
    """Число > 2^31-1 має викликати помилку."""
    t1 = ThreadModel(id=1, name="Overflow")
    # Додаємо START, щоб не впало на його відсутності
    t1.blocks.append(Block(id=1, type="START", next_id=2))
    # Блок з велетенським числом
    t1.blocks.append(Block(id=2, type="ASSIGN", value=9999999999, next_id=3))
    t1.blocks.append(Block(id=3, type="END"))

    empty_project.threads.append(t1)

    is_valid, errors = ProjectValidator.validate(empty_project)
    assert is_valid is False
    assert any("out of 32-bit" in str(e) for e in errors)


def test_generator_output(simple_valid_project):
    """Перевіряємо, чи генератор створює Python код."""
    code = PythonGenerator.generate(simple_valid_project)

    # Перевіряємо ключові фрази в коді
    assert "import threading" in code
    assert "class SharedState:" in code
    assert "def thread_1_Thread_1(shared):" in code
    assert "shared.var0 = to_u32(10)" in code
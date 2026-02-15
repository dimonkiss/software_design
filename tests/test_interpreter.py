from src.core.models import Project, ThreadModel, Block
from src.gui.widgets.interpreter import InterpreterWorker


class MockSignal:
    """Клас для перехоплення сигналів від Worker."""

    def __init__(self):
        self.messages = []

    def emit(self, thread_id, text):
        self.messages.append((thread_id, text))


def test_interpreter_assignment_logic():
    """Тест: START -> ASSIGN(var0=50) -> END."""
    proj = Project()
    t = ThreadModel(id=1, name="Test Thread")  # <--- Додано name

    b1 = Block(id=1, type="START", next_id=2)
    b2 = Block(id=2, type="ASSIGN", target_var="var0", value=50, next_id=3)
    b3 = Block(id=3, type="END")

    t.blocks = [b1, b2, b3]
    proj.threads.append(t)

    worker = InterpreterWorker(proj)
    worker.sig_print = MockSignal()

    worker._execute_thread(t)

    assert worker.shared_memory["var0"] == 50


def test_interpreter_decision_true():
    """Тест: DECISION (10 == 10) -> True path."""
    proj = Project()
    t = ThreadModel(id=1, name="Decision Thread")  # <--- Додано name

    b1 = Block(id=1, type="START", next_id=2)
    b2 = Block(id=2, type="ASSIGN", target_var="var0", value=10, next_id=3)

    b3 = Block(id=3, type="DECISION", target_var="var0", operator="==", value=10, true_next_id=4, false_next_id=5)

    b4 = Block(id=4, type="ASSIGN", target_var="result", value=100, next_id=6)
    b5 = Block(id=5, type="ASSIGN", target_var="result", value=200, next_id=6)
    b6 = Block(id=6, type="END")

    t.blocks = [b1, b2, b3, b4, b5, b6]
    proj.threads.append(t)

    worker = InterpreterWorker(proj)
    worker.sig_print = MockSignal()
    worker._execute_thread(t)

    assert worker.shared_memory["result"] == 100


def test_interpreter_variable_assignment():
    """Тест: V1 = V2 (копіювання значення)."""
    proj = Project()
    t = ThreadModel(id=1, name="Var Assignment Thread")  # <--- Додано name

    b1 = Block(id=1, type="START", next_id=2)
    b2 = Block(id=2, type="ASSIGN", target_var="var1", value=99, next_id=3)
    b3 = Block(id=3, type="ASSIGN", target_var="var2", src_var="var1", next_id=4)
    b4 = Block(id=4, type="END")

    t.blocks = [b1, b2, b3, b4]
    proj.threads.append(t)

    worker = InterpreterWorker(proj)
    worker.sig_print = MockSignal()
    worker._execute_thread(t)

    assert worker.shared_memory["var2"] == 99
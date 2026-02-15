import time
from PySide6.QtCore import QObject, Signal, QMutex
from src.core.models import Project


class InterpreterWorker(QObject):
    sig_print = Signal(int, str)  # thread_id, text
    sig_finished = Signal()
    sig_error = Signal(str)

    def __init__(self, project: Project):
        super().__init__()
        self.project = project
        self.running = True
        # Ініціалізація пам'яті. Якщо змінні не оголошені явно, вони створюються динамічно.
        self.shared_memory = {name: 0 for name in project.shared_variables}
        self.mutex = QMutex()

    def run(self):
        import threading

        threads = []
        for t_model in self.project.threads:
            t = threading.Thread(target=self._execute_thread, args=(t_model,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        self.sig_finished.emit()

    def _execute_thread(self, thread_model):
        current_block = next((b for b in thread_model.blocks if b.type == 'START'), None)
        if not current_block:
            self.sig_print.emit(thread_model.id, "ERROR: No START block found!")
            return

        self.sig_print.emit(thread_model.id, f"--- Thread Started ---")

        while current_block and self.running:
            time.sleep(0.1)

            if current_block.type == 'END':
                self.sig_print.emit(thread_model.id, "--- Thread Finished ---")
                break

            elif current_block.type == 'PRINT':
                val = self._get_var(current_block.target_var)
                self.sig_print.emit(thread_model.id, f"OUTPUT: {val}")
                next_id = current_block.next_id

            elif current_block.type == 'ASSIGN':
                val = 0

                # --- ВИПРАВЛЕНА ЛОГІКА ---
                # 1. Якщо є джерело-змінна, беремо значення з неї
                if current_block.src_var:
                    val = self._get_var(current_block.src_var)
                # 2. Інакше беремо константу (value)
                elif current_block.value is not None:
                    val = current_block.value

                self._set_var(current_block.target_var, val)
                next_id = current_block.next_id

            elif current_block.type == 'DECISION':
                val = self._get_var(current_block.target_var)
                cmp_val = current_block.value if current_block.value is not None else 0
                res = False

                if current_block.operator == '==':
                    res = (val == cmp_val)
                elif current_block.operator == '<':
                    res = (val < cmp_val)

                next_id = current_block.true_next_id if res else current_block.false_next_id

            elif current_block.type == 'INPUT':
                # Емуляція вводу (автоматично 10)
                self.sig_print.emit(thread_model.id, f"INPUT REQUESTED for {current_block.target_var} (Auto: 10)")
                self._set_var(current_block.target_var, 10)
                next_id = current_block.next_id

            elif current_block.type == 'START':
                next_id = current_block.next_id

            else:
                next_id = current_block.next_id

            # Перехід до наступного блоку
            current_block = thread_model.get_block_by_id(next_id)

    def _get_var(self, name):
        self.mutex.lock()
        # Якщо змінної немає, повертаємо 0
        val = self.shared_memory.get(name, 0)
        self.mutex.unlock()
        return val

    def _set_var(self, name, value):
        self.mutex.lock()
        if name:
            self.shared_memory[name] = value
        self.mutex.unlock()

    def stop(self):
        self.running = False
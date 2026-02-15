from typing import List, Tuple

from models import Project, ThreadModel, MAX_VAL, MIN_VAL


class ValidationError:
    """Клас для опису помилки валідації."""

    def __init__(self, message: str, thread_id: int = None, block_id: int = None):
        self.message = message
        self.thread_id = thread_id
        self.block_id = block_id

    def __str__(self):
        location = ""
        if self.thread_id is not None:
            location += f"Thread {self.thread_id}"
        if self.block_id is not None:
            location += f", Block {self.block_id}"
        return f"[{location}] {self.message}" if location else self.message


class ProjectValidator:
    @staticmethod
    def validate(project: Project) -> Tuple[bool, List[ValidationError]]:
        errors = []

        # 1. Валідація загальних обмежень проекту
        if not (1 <= len(project.threads) <= 100):
            errors.append(ValidationError(f"Project must have 1-100 threads (current: {len(project.threads)})"))

        if len(project.shared_variables) > 100:
            errors.append(ValidationError(f"Too many shared variables: {len(project.shared_variables)} (max: 100)"))

        # 2. Валідація кожного потоку
        for thread in project.threads:
            errors.extend(ProjectValidator._validate_thread(thread, project.shared_variables))

        return len(errors) == 0, errors

    @staticmethod
    def _validate_thread(thread: ThreadModel, shared_vars: List[str]) -> List[ValidationError]:
        thread_errors = []

        # Обмеження кількості блоків
        if len(thread.blocks) > 100:
            thread_errors.append(ValidationError("Thread exceeds 100 blocks limit", thread.id))

        if not thread.blocks:
            thread_errors.append(ValidationError("Thread is empty", thread.id))
            return thread_errors

        # Перевірка наявності START та END
        starts = [b for b in thread.blocks if b.type == 'START']
        ends = [b for b in thread.blocks if b.type == 'END']

        if len(starts) != 1:
            thread_errors.append(
                ValidationError(f"Thread must have exactly 1 START block (found: {len(starts)})", thread.id))

        if len(ends) < 1:
            thread_errors.append(ValidationError("Thread must have at least 1 END block", thread.id))

        # Валідація кожного блоку
        block_ids = {b.id for b in thread.blocks}

        for block in thread.blocks:
            # Перевірка діапазону значень (згідно ТЗ: 0...2^31-1)
            if block.value is not None:
                if not (MIN_VAL <= block.value <= MAX_VAL):
                    thread_errors.append(ValidationError(
                        f"Value {block.value} is out of 32-bit unsigned range", thread.id, block.id
                    ))

            # Перевірка використання змінних
            for var_name in [block.target_var, block.src_var]:
                if var_name and var_name not in shared_vars:
                    thread_errors.append(ValidationError(
                        f"Variable '{var_name}' is not registered in shared memory", thread.id, block.id
                    ))

            # Перевірка цілісності зв'язків (чи існують блоки, на які ми посилаємось)
            if block.type == 'DECISION':
                if block.true_next_id not in block_ids:
                    thread_errors.append(
                        ValidationError("Branch 'True' points to non-existent block", thread.id, block.id))
                if block.false_next_id not in block_ids:
                    thread_errors.append(
                        ValidationError("Branch 'False' points to non-existent block", thread.id, block.id))
            elif block.type != 'END':
                if block.next_id not in block_ids:
                    thread_errors.append(
                        ValidationError(f"Block points to non-existent next block (ID: {block.next_id})", thread.id,
                                        block.id))

        return thread_errors
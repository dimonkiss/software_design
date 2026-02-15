
from src.core.models import Project, ThreadModel


class PythonGenerator:
    @staticmethod
    def generate(project: Project) -> str:
        lines = []

        # 1. Imports
        lines.append("import threading")
        lines.append("import time")
        lines.append("import sys")
        lines.append("")

        # 2. Helper for 32-bit unsigned wrap
        lines.append("def to_u32(val):")
        lines.append("    return val & 0xFFFFFFFF")
        lines.append("")

        # 3. Shared State Class
        lines.append("class SharedState:")
        lines.append("    def __init__(self):")
        if not project.shared_variables:
            lines.append("        pass")
        else:
            for var in project.shared_variables:
                lines.append(f"        self.{var} = 0")
        lines.append("")

        # 4. Thread Functions
        for thread in project.threads:
            # Генеруємо функцію тільки якщо є блоки
            if thread.blocks:
                lines.extend(PythonGenerator._generate_thread_func(thread))
                lines.append("")

        # 5. Main Entry Point
        lines.append("if __name__ == '__main__':")
        lines.append("    shared = SharedState()")
        lines.append("    threads = []")
        lines.append("")

        for thread in project.threads:
            # Перевіряємо, чи є START блок перед запуском
            start_block = next((b for b in thread.blocks if b.type == 'START'), None)
            if start_block:
                func_name = f"thread_{thread.id}_{thread.name.replace(' ', '_')}"
                lines.append(f"    t{thread.id} = threading.Thread(target={func_name}, args=(shared,))")
                lines.append(f"    threads.append(t{thread.id})")
                lines.append(f"    t{thread.id}.start()")
            else:
                lines.append(f"    print('Skipping Thread {thread.id}: No START block found')")

        lines.append("")
        lines.append("    for t in threads:")
        lines.append("        t.join()")
        lines.append("    print('All threads finished.')")

        return "\n".join(lines)

    @staticmethod
    def _generate_thread_func(thread: ThreadModel) -> list:
        lines = []
        func_name = f"thread_{thread.id}_{thread.name.replace(' ', '_')}"
        lines.append(f"def {func_name}(shared):")

        # Знаходимо Start блок
        start_block = next((b for b in thread.blocks if b.type == 'START'), None)

        # --- ЗАХИСТ ВІД ПОРОЖНЬОГО ПОТОКУ ---
        if not start_block:
            lines.append("    print('Error: No START block found')")
            lines.append("    return")
            return lines  # Важливо: виходимо, щоб не викликати помилку .id
        # ------------------------------------

        lines.append(f"    current_block_id = {start_block.id}")
        lines.append(f"    print(f'Thread {{threading.current_thread().name}} started')")

        lines.append("    while current_block_id is not None:")

        first = True
        for block in thread.blocks:
            prefix = "if" if first else "elif"
            lines.append(f"        {prefix} current_block_id == {block.id}:")
            first = False

            if block.type == 'START':
                lines.append(f"            current_block_id = {block.next_id}")

            elif block.type == 'END':
                lines.append("            current_block_id = None")

            elif block.type == 'ASSIGN':
                rhs = str(block.value)
                lines.append(f"            # ASSIGN {block.target_var} = {rhs}")
                if block.target_var:
                    lines.append(f"            shared.{block.target_var} = to_u32({rhs})")
                lines.append(f"            current_block_id = {block.next_id}")

            elif block.type == 'PRINT':
                lines.append(f"            print(f'OUTPUT: {{shared.{block.target_var}}}')")
                lines.append(f"            current_block_id = {block.next_id}")

            elif block.type == 'INPUT':
                lines.append(f"            try:")
                lines.append(f"                val = int(input(f'INPUT {block.target_var}: '))")
                lines.append(f"                shared.{block.target_var} = to_u32(val)")
                lines.append(f"            except ValueError:")
                lines.append(f"                print('Invalid input, using 0')")
                lines.append(f"                shared.{block.target_var} = 0")
                lines.append(f"            current_block_id = {block.next_id}")

            elif block.type == 'DECISION':
                op = "==" if block.operator == "==" else "<"
                lines.append(f"            if shared.{block.target_var} {op} {block.value}:")
                lines.append(f"                current_block_id = {block.true_next_id}")
                lines.append(f"            else:")
                lines.append(f"                current_block_id = {block.false_next_id}")

            # Захист від блоків без виходу
            if block.type not in ('END', 'DECISION') and block.next_id is None:
                lines.append("            # Warning: Dead end here")
                lines.append("            current_block_id = None")

        return lines
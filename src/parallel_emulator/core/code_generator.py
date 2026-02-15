import json
from pathlib import Path

from src.parallel_emulator.domain.entities.block import Block
from src.parallel_emulator.domain.entities.project import Project
from src.parallel_emulator.domain.entities.thread import Thread
from src.parallel_emulator.domain.enums.block_type import BlockType


class CodeGenerator:
    def __init__(self, project: Project):
        self.project = project

    def generate_code(self, output_dir: Path):
        output_dir.mkdir(exist_ok=True)

        # shared_memory.json
        shared_path = output_dir / "shared_memory.json"
        shared_data = {var: 0 for var in self.project.variables}
        with open(shared_path, "w", encoding="utf-8") as f:
            json.dump(shared_data, f, indent=2)

        # Генерація файлів для кожного потоку
        for thread in self.project.threads:
            thread_file = output_dir / f"thread_{thread.id}.py"
            with open(thread_file, "w", encoding="utf-8") as f:
                f.write(self._generate_thread_file(thread, output_dir))

        # main_launcher.py
        launcher_path = output_dir / "main_launcher.py"
        with open(launcher_path, "w", encoding="utf-8") as f:
            f.write(self._generate_launcher(output_dir))

        return launcher_path

    def _generate_launcher(self, output_dir: Path) -> str:
        lines = [
            "import subprocess",
            "import time",
            "from pathlib import Path",
            "",
            "if __name__ == '__main__':",
            "    dir_path = Path(__file__).parent",
            "    threads = ["
        ]
        for thread in self.project.threads:
            lines.append(f"        {thread.id},")
        lines.append("    ]")
        lines.append("")
        lines.append("    for tid in threads:")
        lines.append("        script = dir_path / f'thread_{tid}.py'")
        lines.append("        cmd = f'start \"Thread {tid}\" cmd /k python \"{script}\"'")
        lines.append("        subprocess.Popen(cmd, shell=True)")
        lines.append("    print('Усі термінали запущено. Закрийте вікна, коли завершите.')")
        return "\n".join(lines)

    def _generate_thread_file(self, thread: Thread, output_dir: Path) -> str:
        shared_path = output_dir / "shared_memory.json"
        lines = [
            "import json",
            "import time",
            "from pathlib import Path",
            "",
            f"SHARED_FILE = Path(r'{shared_path}')",
            "LOCK_FILE = SHARED_FILE.with_suffix('.lock')",
            "",
            "def lock():",
            "    while LOCK_FILE.exists():",
            "        time.sleep(0.05)",
            "    LOCK_FILE.touch()",
            "",
            "def unlock():",
            "    if LOCK_FILE.exists():",
            "        LOCK_FILE.unlink()",
            "",
            "def read_shared():",
            "    lock()",
            "    try:",
            "        with open(SHARED_FILE, 'r', encoding='utf-8') as f:",
            "            return json.load(f)",
            "    except:",
            "        return {}",
            "    finally:",
            "        unlock()",
            "",
            "def write_shared(data):",
            "    lock()",
            "    try:",
            "        with open(SHARED_FILE, 'w', encoding='utf-8') as f:",
            "            json.dump(data, f, indent=2)",
            "    finally:",
            "        unlock()",
            "",
            f"print('[Thread {thread.id}] Початок виконання')",
            "current = None"
        ]

        # START
        start_block = next((b for b in thread.blocks.values() if b.type == BlockType.START), None)
        if start_block and start_block.next is not None:
            lines.append(f"current = {start_block.next}")

        lines.append("while current is not None:")
        lines.append("    shared = read_shared()")
        lines.append("    executed = False")

        for block in thread.blocks.values():
            lines.extend(self._generate_block_code(block, thread.id))

        lines.append("    if not executed:")
        lines.append(f"        print('[Thread {thread.id}] Невідомий блок:', current)")
        lines.append("        current = None")

        lines.append(f"print('[Thread {thread.id}] Завершено')")
        return "\n".join(lines)

    def _generate_block_code(self, block: Block, thread_id: int) -> list[str]:
        indent = "    "
        lines = [f"{indent}if current == {block.id} and not executed:"]
        indent2 = indent + "    "
        lines.append(f"{indent2}executed = True")

        prefix = f"[Thread {thread_id}] "

        if block.type == BlockType.ASSIGN:
            if block.source.type == "const":
                lines.append(f"{indent2}shared['{block.target}'] = {block.source.value} & 0xFFFFFFFF")
            else:
                lines.append(f"{indent2}shared['{block.target}'] = shared.get('{block.source.value}', 0) & 0xFFFFFFFF")
            lines.append(f"{indent2}write_shared(shared)")
            if block.next:
                lines.append(f"{indent2}current = {block.next}")
            else:
                lines.append(f"{indent2}current = None")

        elif block.type == BlockType.INPUT:
            lines.append(f"{indent2}value = int(input('{prefix}INPUT {block.io_var} > '))")
            lines.append(f"{indent2}shared['{block.io_var}'] = value & 0xFFFFFFFF")
            lines.append(f"{indent2}write_shared(shared)")
            if block.next:
                lines.append(f"{indent2}current = {block.next}")
            else:
                lines.append(f"{indent2}current = None")

        elif block.type == BlockType.PRINT:
            lines.append(f"{indent2}print('{prefix}PRINT {block.io_var}: {{shared.get(\"{block.io_var}\", 0)}}')")
            if block.next:
                lines.append(f"{indent2}current = {block.next}")
            else:
                lines.append(f"{indent2}current = None")

        elif block.type == BlockType.DECISION:
            var_val = f"shared.get('{block.condition.var}', 0)"
            cond = f"{var_val} == {block.condition.const}" if block.condition.op == "==" else f"{var_val} < {block.condition.const}"
            lines.append(f"{indent2}if {cond}:")
            if block.true_next:
                lines.append(f"{indent2}    current = {block.true_next}")
            else:
                lines.append(f"{indent2}    current = None")
            lines.append(f"{indent2}else:")
            if block.false_next:
                lines.append(f"{indent2}    current = {block.false_next}")
            else:
                lines.append(f"{indent2}    current = None")

        elif block.type == BlockType.END:
            lines.append(f"{indent2}current = None")

        return lines
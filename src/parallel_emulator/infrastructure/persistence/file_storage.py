from pathlib import Path
from typing import List
from uuid import UUID
import orjson

class FileStorage:
    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def get_project_path(self, project_id: UUID) -> Path:
        return self.base_dir / f"{project_id}.json"

    def list_project_files(self) -> List[Path]:
        return list(self.base_dir.glob("*.json"))

    def save(self, path: Path, data: dict) -> None:
        with open(path, "wb") as f:
            f.write(orjson.dumps(data, option=orjson.OPT_INDENT_2))

    def load(self, path: Path) -> dict:
        with open(path, "rb") as f:
            return orjson.loads(f.read())

    def delete(self, path: Path) -> bool:
        if path.exists():
            path.unlink()
            return True
        return False
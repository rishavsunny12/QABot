from pathlib import Path

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("ArtifactService")


class ArtifactService:
    """Manage filesystem artifact paths and serving."""

    def __init__(self, base_dir: str | None = None) -> None:
        self.base_dir = Path(base_dir or settings.artifacts_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def project_dir(self, project_id: str) -> Path:
        path = self.base_dir / "projects" / project_id
        path.mkdir(parents=True, exist_ok=True)
        return path

    def crawl_dir(self, project_id: str) -> Path:
        path = self.project_dir(project_id) / "crawls"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def tests_dir(self, project_id: str) -> Path:
        path = self.project_dir(project_id) / "tests"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def run_dir(self, run_id: str) -> Path:
        path = self.base_dir / "runs" / run_id
        path.mkdir(parents=True, exist_ok=True)
        return path

    def resolve_path(self, relative_path: str) -> Path:
        path = Path(relative_path)
        if not path.is_absolute():
            path = self.base_dir / relative_path
        return path.resolve()

    def to_relative(self, absolute_path: str | Path) -> str:
        abs_path = Path(absolute_path).resolve()
        try:
            return str(abs_path.relative_to(self.base_dir.resolve()))
        except ValueError:
            return str(abs_path)

    def exists(self, relative_path: str) -> bool:
        return self.resolve_path(relative_path).exists()


artifact_service = ArtifactService()

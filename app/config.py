import os
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class Settings:
    model: str = os.getenv("PM_MODEL", "claude-opus-5-5")
    effort: str = os.getenv("PM_EFFORT", "high")
    db_path: str = os.getenv("PM_DB_PATH", str(ROOT / "pm_harness.db"))
    context_dir: Path = Path(os.getenv("PM_CONTEXT_DIR", str(ROOT / "context")))
    signals_dir: Path = Path(os.getenv("PM_SIGNALS_DIR", str(ROOT / "signals")))
    notion_token: str | None = os.getenv("NOTION_TOKEN") or None
    notion_parent_page_id: str | None = os.getenv("NOTION_PARENT_PAGE_ID") or None


settings = Settings()

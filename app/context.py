"""Loads company context and raw signals as tagged text the agents can cite by id."""

from pathlib import Path


def _tagged(path: Path, root: Path) -> str:
    source_id = str(path.relative_to(root)).replace("\\", "/")
    return f'<source id="{source_id}">\n{path.read_text().strip()}\n</source>'


def load_dir(root: Path, pattern: str = "*") -> str:
    files = sorted(p for p in root.rglob(pattern) if p.is_file() and not p.name.startswith("."))
    return "\n\n".join(_tagged(p, root) for p in files)

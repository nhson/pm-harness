"""SQLite artifact store and gate table. Every run writes a new artifact version."""

import json
import sqlite3
from datetime import datetime, timezone

from pydantic import BaseModel

SCHEMA = """
create table if not exists artifacts (
  id integer primary key autoincrement,
  layer text not null,
  kind text not null,
  body text not null,
  notion_url text,
  created_at text not null
);
create table if not exists gates (
  artifact_id integer primary key references artifacts(id),
  layer text not null,
  status text not null check (status in ('pending', 'approved', 'rejected')),
  decision text,
  decided_at text
);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class Store:
    def __init__(self, path: str):
        self.db = sqlite3.connect(path, check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.db.executescript(SCHEMA)

    def save(self, layer: str, kind: str, artifact: BaseModel, gated: bool) -> int:
        cur = self.db.execute(
            "insert into artifacts (layer, kind, body, created_at) values (?, ?, ?, ?)",
            (layer, kind, artifact.model_dump_json(), _now()),
        )
        artifact_id = cur.lastrowid
        if gated:
            self.db.execute(
                "insert into gates (artifact_id, layer, status) values (?, ?, 'pending')",
                (artifact_id, layer),
            )
        self.db.commit()
        return artifact_id

    def set_notion_url(self, artifact_id: int, url: str) -> None:
        self.db.execute("update artifacts set notion_url = ? where id = ?", (url, artifact_id))
        self.db.commit()

    def get(self, artifact_id: int) -> dict | None:
        row = self.db.execute("select * from artifacts where id = ?", (artifact_id,)).fetchone()
        return self._row(row) if row else None

    def latest(self, layer: str, kind: str) -> dict | None:
        row = self.db.execute(
            "select * from artifacts where layer = ? and kind = ? order by id desc limit 1", (layer, kind)
        ).fetchone()
        return self._row(row) if row else None

    def latest_approved(self, layer: str) -> dict | None:
        row = self.db.execute(
            """select a.* from artifacts a join gates g on g.artifact_id = a.id
               where g.layer = ? and g.status = 'approved' order by a.id desc limit 1""",
            (layer,),
        ).fetchone()
        return self._row(row) if row else None

    def list(self, layer: str | None = None) -> list[dict]:
        sql, args = "select * from artifacts", ()
        if layer:
            sql, args = sql + " where layer = ?", (layer,)
        return [self._row(r) for r in self.db.execute(sql + " order by id desc", args)]

    def decide(self, artifact_id: int, approve: bool, decision: str | None) -> dict:
        status = "approved" if approve else "rejected"
        cur = self.db.execute(
            "update gates set status = ?, decision = ?, decided_at = ? where artifact_id = ?",
            (status, decision, _now(), artifact_id),
        )
        if cur.rowcount == 0:
            raise KeyError(artifact_id)
        self.db.commit()
        return dict(self.db.execute("select * from gates where artifact_id = ?", (artifact_id,)).fetchone())

    @staticmethod
    def _row(row: sqlite3.Row) -> dict:
        d = dict(row)
        d["body"] = json.loads(d["body"])
        return d

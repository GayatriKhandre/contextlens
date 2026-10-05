from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

DB_PATH = Path(os.getenv("CONTEXTLENS_DB", Path(__file__).with_name("contextlens.db")))


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db() -> None:
    with connect() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS cases (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                preview TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                problem TEXT NOT NULL,
                about TEXT NOT NULL,
                mode TEXT NOT NULL,
                use_personal_context INTEGER NOT NULL DEFAULT 0,
                context_json TEXT NOT NULL DEFAULT '{}',
                question_json TEXT NOT NULL DEFAULT '{}',
                analysis_json TEXT NOT NULL DEFAULT '{}',
                decision_json TEXT
            );
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                case_id TEXT NOT NULL,
                kind TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(case_id) REFERENCES cases(id)
            );
            CREATE TABLE IF NOT EXISTS personal_context (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                content TEXT NOT NULL DEFAULT '',
                enabled INTEGER NOT NULL DEFAULT 0,
                updated_at TEXT NOT NULL
            );
            """
        )


def dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False)


def loads(value: Optional[str]) -> Any:
    if not value:
        return {}
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return {}


def case_from_row(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "title": row["title"],
        "preview": row["preview"],
        "status": row["status"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "problem": row["problem"],
        "about": row["about"],
        "mode": row["mode"],
        "use_personal_context": bool(row["use_personal_context"]),
        "context": loads(row["context_json"]),
        "question": loads(row["question_json"]),
        "analysis": loads(row["analysis_json"]),
        "decision": loads(row["decision_json"]) if row["decision_json"] else None,
    }


def create_case(case: dict[str, Any]) -> dict[str, Any]:
    with connect() as conn:
        conn.execute(
            """INSERT INTO cases (id, title, preview, status, created_at, updated_at, problem, about, mode,
            use_personal_context, context_json, question_json, analysis_json) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                case["id"], case["title"], case["preview"], case["status"], case["created_at"], case["updated_at"],
                case["problem"], case["about"], case["mode"], int(case["use_personal_context"]), dumps(case["context"]),
                dumps(case["question"]), dumps(case.get("analysis", {})),
            ),
        )
        add_event(conn, case["id"], "created", {"context": case["context"], "question": case["question"]})
    return case


def update_case(case_id: str, *, status: Optional[str] = None, context: Any = None, question: Any = None,
                analysis: Any = None, decision: Any = None) -> Optional[dict[str, Any]]:
    with connect() as conn:
        row = conn.execute("SELECT * FROM cases WHERE id = ?", (case_id,)).fetchone()
        if not row:
            return None
        existing = case_from_row(row)
        new_status = status or existing["status"]
        new_context = existing["context"] if context is None else context
        new_question = existing["question"] if question is None else question
        new_analysis = existing["analysis"] if analysis is None else analysis
        new_decision = existing["decision"] if decision is None else decision
        updated_at = now_iso()
        conn.execute(
            """UPDATE cases SET status=?, updated_at=?, context_json=?, question_json=?, analysis_json=?, decision_json=? WHERE id=?""",
            (new_status, updated_at, dumps(new_context), dumps(new_question), dumps(new_analysis), dumps(new_decision) if new_decision is not None else None, case_id),
        )
        if context is not None:
            add_event(conn, case_id, "context_updated", {"context": context})
        if question is not None:
            add_event(conn, case_id, "question_updated", {"question": question})
        if analysis is not None:
            add_event(conn, case_id, "analysis_created", {"analysis": analysis})
        if decision is not None:
            add_event(conn, case_id, "decision_saved", {"decision": decision})
        row = conn.execute("SELECT * FROM cases WHERE id = ?", (case_id,)).fetchone()
        return case_from_row(row)


def add_event(conn: sqlite3.Connection, case_id: str, kind: str, payload: Any) -> None:
    conn.execute("INSERT INTO events (case_id, kind, payload_json, created_at) VALUES (?, ?, ?, ?)", (case_id, kind, dumps(payload), now_iso()))


def get_case(case_id: str) -> Optional[dict[str, Any]]:
    with connect() as conn:
        row = conn.execute("SELECT * FROM cases WHERE id = ?", (case_id,)).fetchone()
        return case_from_row(row) if row else None


def list_cases() -> list[dict[str, Any]]:
    with connect() as conn:
        rows = conn.execute("SELECT * FROM cases ORDER BY updated_at DESC").fetchall()
        return [case_from_row(row) for row in rows]


def list_decisions() -> list[dict[str, Any]]:
    return [case for case in list_cases() if case.get("decision")]


def replay(case_id: str) -> Optional[dict[str, Any]]:
    case = get_case(case_id)
    if not case:
        return None
    with connect() as conn:
        events = conn.execute("SELECT kind, payload_json, created_at FROM events WHERE case_id = ? ORDER BY id", (case_id,)).fetchall()
    case["events"] = [{"kind": row["kind"], "payload": loads(row["payload_json"]), "created_at": row["created_at"]} for row in events]
    return case


def get_personal_context() -> dict[str, Any]:
    with connect() as conn:
        row = conn.execute("SELECT content, enabled, updated_at FROM personal_context WHERE id = 1").fetchone()
    if not row:
        return {"content": "", "enabled": False, "updated_at": None}
    return {"content": row["content"], "enabled": bool(row["enabled"]), "updated_at": row["updated_at"]}


def save_personal_context(content: str, enabled: bool) -> dict[str, Any]:
    timestamp = now_iso()
    with connect() as conn:
        conn.execute("INSERT INTO personal_context (id, content, enabled, updated_at) VALUES (1, ?, ?, ?) ON CONFLICT(id) DO UPDATE SET content=excluded.content, enabled=excluded.enabled, updated_at=excluded.updated_at", (content, int(enabled), timestamp))
    return {"content": content, "enabled": enabled, "updated_at": timestamp}


def clear_all() -> None:
    with connect() as conn:
        conn.execute("DELETE FROM events")
        conn.execute("DELETE FROM cases")
        conn.execute("DELETE FROM personal_context")

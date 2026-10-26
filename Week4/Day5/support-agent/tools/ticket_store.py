"""
STEP 3 — Manual entry storage
When the answer is in neither your content nor the web, the customer's details
are entered manually and saved here (SQLite database: data/support.db).
"""
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Type

from crewai.tools import BaseTool
from pydantic import BaseModel, Field

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "support.db"


def _conn():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS tickets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT,
            name TEXT, email TEXT, phone TEXT,
            question TEXT, details TEXT,
            summary TEXT, priority TEXT,
            status TEXT DEFAULT 'OPEN',
            answer TEXT
        )""")
    return conn


def save_ticket(name, email, phone, question, details, summary="", priority="MEDIUM") -> int:
    with _conn() as conn:
        cur = conn.execute(
            "INSERT INTO tickets (created_at,name,email,phone,question,details,summary,priority)"
            " VALUES (?,?,?,?,?,?,?,?)",
            (datetime.now().isoformat(timespec="seconds"), name, email, phone,
             question, details, summary, priority))
        return cur.lastrowid


def update_ticket(ticket_id: int, **fields) -> None:
    cols = ", ".join(f"{k}=?" for k in fields)
    with _conn() as conn:
        conn.execute(f"UPDATE tickets SET {cols} WHERE id=?", (*fields.values(), ticket_id))


def list_tickets(status: str | None = None) -> list[dict]:
    with _conn() as conn:
        conn.row_factory = sqlite3.Row
        sql = "SELECT * FROM tickets" + (" WHERE status=?" if status else "") + " ORDER BY id DESC"
        return [dict(r) for r in conn.execute(sql, (status,) if status else ())]


class TicketUpdateInput(BaseModel):
    ticket_id: int = Field(..., description="ID of the ticket that was just saved")
    summary: str = Field(..., description="One-paragraph summary of the customer's issue")
    priority: str = Field(..., description="LOW, MEDIUM or HIGH")


class UpdateTicketTool(BaseTool):
    name: str = "update_support_ticket"
    description: str = "Saves the issue summary and priority on an existing support ticket."
    args_schema: Type[BaseModel] = TicketUpdateInput

    def _run(self, ticket_id: int, summary: str, priority: str) -> str:
        update_ticket(ticket_id, summary=summary, priority=priority.upper())
        return f"Ticket #{ticket_id} updated (priority {priority.upper()})."

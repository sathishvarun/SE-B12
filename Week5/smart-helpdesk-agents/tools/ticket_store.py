"""Ticket logging (CSV + TXT), the escalation rules and the human review (human-in-the-loop) updates."""
import csv
import threading
from datetime import datetime

import pandas as pd

from config import DEPARTMENT_LABELS, LOG_CSV, LOG_TXT

COLUMNS = [
    "ticket_id", "timestamp", "employee_name", "employee_id", "department", "category",
    "priority", "sentiment", "summary", "complaint", "kb_sources", "response",
    "confidence", "status", "escalation_reason", "assigned_to",
    # human-in-the-loop: escalated tickets wait for a person to approve the reply
    "review_status", "reviewer", "final_response", "reviewed_at",
]

REVIEW_PENDING, REVIEW_APPROVED, REVIEW_CLOSED, REVIEW_NOT_NEEDED = (
    "Pending review", "Approved", "Handled by team", "Not needed")

RISK_WORDS = {
    "legal threat": ["lawyer", "legal", "sue", "court", "police", "consumer forum"],
    "fraud": ["fraud", "scam", "stolen", "hacked", "unauthori"],
    "payment dispute": ["chargeback", "charged twice", "charged three", "charged my card", "double charge",
                        "my bank", "dispute"],
    "workplace complaint": ["harass", "discriminat", "abuse", "threaten", "unsafe"],
}

_lock = threading.RLock()


def next_ticket_id() -> str:
    count = len(load_tickets())
    return f"TKT-{count + 1:04d}"


def escalation_check(ticket: dict, agent_says_escalate: bool = False, agent_reason: str = "") -> list[str]:
    """Return the list of reasons to escalate. Empty list = can be resolved by AI."""
    reasons = []
    if ticket.get("priority") == "High":
        reasons.append("High priority")
    if ticket.get("sentiment") == "Angry":
        reasons.append("Very angry employee/client")
    if not ticket.get("kb_sources") or ticket.get("kb_sources") == "NONE":
        reasons.append("No matching document in knowledge base")
    if ticket.get("confidence") == "Low":
        reasons.append("Low confidence answer")
    text = ticket.get("complaint", "").lower()
    for label, words in RISK_WORDS.items():
        if any(w in text for w in words):
            reasons.append(f"Involves {label}")
    if agent_says_escalate and agent_reason:
        reasons.append(f"Log Agent: {agent_reason}")
    # keep order, remove duplicates
    return list(dict.fromkeys(reasons))


def save_ticket(ticket: dict) -> dict:
    """Append one ticket to logs/tickets.csv and logs/tickets.txt."""
    row = {c: ticket.get(c, "") for c in COLUMNS}
    with _lock:
        _upgrade_old_log()
        new_file = not LOG_CSV.exists()
        with open(LOG_CSV, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=COLUMNS)
            if new_file:
                writer.writeheader()
            writer.writerow(row)
        with open(LOG_TXT, "a", encoding="utf-8") as f:
            f.write(
                f"{'=' * 70}\n"
                f"{row['ticket_id']} | {row['timestamp']} | {row['status'].upper()}\n"
                f"From       : {row['employee_name'] or '-'} | Employee ID: {row['employee_id'] or '-'}\n"
                f"Department : {row['department']} | Category: {row['category']}\n"
                f"Priority   : {row['priority']} | Sentiment: {row['sentiment']} | Confidence: {row['confidence']}\n"
                f"Query      : {row['complaint']}\n"
                f"Sources    : {row['kb_sources']}\n"
                f"Reply      : {row['response']}\n"
                f"Escalation : {row['escalation_reason'] or '-'} -> {row['assigned_to']}\n\n"
            )
    return row


def build_row(ctx: dict, response: str, confidence: str, kb_sources: str,
              agent_escalate: bool = False, agent_reason: str = "") -> dict:
    ticket = dict(ctx)
    ticket.update({
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "response": response.strip(),
        "confidence": confidence if confidence in ("High", "Medium", "Low") else "Low",
        "kb_sources": kb_sources or "NONE",
    })
    reasons = escalation_check(ticket, agent_escalate, agent_reason)
    dept_label = DEPARTMENT_LABELS.get(ticket.get("department_key", ""), ticket.get("department", ""))
    ticket["status"] = "Escalated" if reasons else "Resolved"
    ticket["escalation_reason"] = " + ".join(reasons)
    ticket["assigned_to"] = f"{dept_label} human team" if reasons else "AI Agent"
    # Escalated replies are HELD as a draft until a person approves them in the Review queue.
    ticket["review_status"] = REVIEW_PENDING if reasons else REVIEW_NOT_NEEDED
    return ticket


def update_review(ticket_id: str, review_status: str, reviewer: str, final_response: str) -> dict:
    """Record a person's decision on an escalated ticket (CSV row updated + TXT log entry)."""
    with _lock:
        _upgrade_old_log()
        df = pd.read_csv(LOG_CSV, dtype=str).fillna("")
        mask = df["ticket_id"] == ticket_id
        if not mask.any():
            raise KeyError(f"Ticket {ticket_id} not found")
        when = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        df.loc[mask, ["review_status", "reviewer", "final_response", "reviewed_at"]] = [
            review_status, reviewer, final_response.strip(), when]
        df.to_csv(LOG_CSV, index=False)
        with open(LOG_TXT, "a", encoding="utf-8") as f:
            f.write(f"{'-' * 70}\nREVIEW {ticket_id} | {when} | {review_status.upper()} by {reviewer}\n"
                    f"Final reply: {final_response.strip()}\n\n")
        return df[mask].iloc[0].to_dict()


def _upgrade_old_log():
    """Older versions used customer_name/order_id columns: rename them once."""
    if not LOG_CSV.exists():
        return
    with open(LOG_CSV, encoding="utf-8") as f:
        header = f.readline().strip().split(",")
    if header != COLUMNS:
        df = pd.read_csv(LOG_CSV, dtype=str).fillna("")
        df = df.rename(columns={"customer_name": "employee_name", "order_id": "employee_id"})
        df = df.reindex(columns=COLUMNS, fill_value="")
        empty = df["review_status"] == ""
        df.loc[empty, "review_status"] = df.loc[empty, "status"].map(
            lambda s: REVIEW_PENDING if s == "Escalated" else REVIEW_NOT_NEEDED)
        df.to_csv(LOG_CSV, index=False)


def load_tickets() -> pd.DataFrame:
    if not LOG_CSV.exists():
        return pd.DataFrame(columns=COLUMNS)
    _upgrade_old_log()
    return pd.read_csv(LOG_CSV, dtype=str).fillna("")

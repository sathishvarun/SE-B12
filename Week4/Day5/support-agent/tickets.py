"""View and answer the manually stored customer entries (Step 3).

    python tickets.py              -> list all tickets
    python tickets.py open         -> list only OPEN tickets
    python tickets.py answer 3     -> answer ticket #3; the answer is also added
                                      to the knowledge base, so Step 1 can answer
                                      the same question next time.
"""
import sys

from dotenv import load_dotenv

load_dotenv()

from tools.rag_tool import add_text  # noqa: E402
from tools.ticket_store import list_tickets, update_ticket  # noqa: E402


def show(status=None):
    rows = list_tickets(status)
    if not rows:
        print("No tickets yet.")
        return
    for t in rows:
        print(f"\n#{t['id']}  [{t['status']}]  priority={t['priority']}  {t['created_at']}")
        print(f"  Customer : {t['name']} | {t['email']} | {t['phone']}")
        print(f"  Question : {t['question']}")
        print(f"  Details  : {t['details']}")
        if t["summary"]:
            print(f"  Summary  : {t['summary']}")
        if t["answer"]:
            print(f"  Answer   : {t['answer']}")


def answer(ticket_id: int):
    ticket = next((t for t in list_tickets() if t["id"] == ticket_id), None)
    if not ticket:
        print(f"Ticket #{ticket_id} not found.")
        return
    print(f"Question: {ticket['question']}")
    text = input("Your answer: ").strip()
    update_ticket(ticket_id, answer=text, status="RESOLVED")
    add_text(f"ticket-{ticket_id}", f"Q: {ticket['question']}\nA: {text}", f"ticket #{ticket_id}")
    print(f"✔ Ticket #{ticket_id} resolved and added to the knowledge base.")


if __name__ == "__main__":
    args = sys.argv[1:]
    if args[:1] == ["answer"] and len(args) == 2:
        answer(int(args[1]))
    else:
        show("OPEN" if args[:1] == ["open"] else None)

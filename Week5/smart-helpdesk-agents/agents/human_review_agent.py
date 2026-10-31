"""HUMAN-IN-THE-LOOP: a support person approves (or edits) the AI's reply on escalated tickets.

Flow:
  1. The Log Agent marks a ticket "Escalated" -> its AI reply is held as a DRAFT (review_status = Pending review).
  2. A team member opens the Review queue page, reads the draft, edits it if needed and decides.
  3. That decision is given to AutoGen's UserProxyAgent ("Human_Reviewer") through its input_func,
     so the human's answer becomes a normal agent message in the AutoGen conversation.
  4. The decision is parsed and saved on the ticket; the employee then sees the approved reply.
"""
import re

from autogen_agentchat.agents import UserProxyAgent

from tools.ticket_store import REVIEW_APPROVED, REVIEW_CLOSED, update_review

DECISIONS = {"APPROVE": REVIEW_APPROVED, "CLOSE": REVIEW_CLOSED}


def create_human_reviewer(reviewer_input: str) -> UserProxyAgent:
    """A UserProxyAgent whose 'keyboard' is the Review queue page: it answers with what the person entered."""
    return UserProxyAgent(
        name="Human_Reviewer",
        description="A support team member who approves, edits or closes escalated tickets.",
        input_func=lambda prompt: reviewer_input,
    )


async def record_human_decision(ticket: dict, decision: str, reviewer: str, final_reply: str) -> dict:
    """Run the Human_Reviewer agent on the AI draft and save the person's decision on the ticket.

    decision = "APPROVE" (send final_reply to the employee) or "CLOSE" (team handled it directly;
    final_reply is the note the employee sees).
    """
    if decision not in DECISIONS:
        raise ValueError(f"Unknown decision {decision}")
    if not final_reply.strip():
        raise ValueError("The reply to the employee cannot be empty.")

    reviewer_input = f"DECISION: {decision}\nREVIEWER: {reviewer}\nFINAL REPLY:\n{final_reply.strip()}"
    human = create_human_reviewer(reviewer_input)
    task = (f"Escalated ticket {ticket['ticket_id']} for the {ticket['department']} team.\n"
            f"Question: {ticket['complaint']}\nWhy escalated: {ticket['escalation_reason']}\n"
            f"AI draft reply:\n{ticket['response']}\n\n"
            "Approve or edit the reply, or close it if your team handled it directly.")
    result = await human.run(task=task)
    answer = result.messages[-1].content            # the human's message, as recorded by AutoGen

    m = re.search(r"DECISION:\s*(APPROVE|CLOSE)", answer)
    final = answer.split("FINAL REPLY:", 1)[-1].strip()
    return update_review(ticket["ticket_id"], DECISIONS[m.group(1) if m else decision], reviewer, final)

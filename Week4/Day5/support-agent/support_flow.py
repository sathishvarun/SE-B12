"""
The CrewAI Flow with the 3-step fallback. Shared by the web app (app.py)
and the terminal version (main.py).

   Question
      │
      ▼
  STEP 1  Knowledge Base Agent (RAG on your content) ── found? ──► Answer
      │ not found
      ▼
  STEP 2  Web Research Agent (Serper + scraper) ─────── found? ──► Answer
      │ not found
      ▼
  STEP 3  Manual entry → saved in SQLite → Escalation Agent ─────► Ticket #
"""
import os

from dotenv import load_dotenv

load_dotenv()
os.environ.setdefault("CREWAI_TRACING_ENABLED", "false")
os.environ.setdefault("CREWAI_DISABLE_TELEMETRY", "true")

from crewai.flow.flow import Flow, listen, router, start  # noqa: E402
from pydantic import BaseModel  # noqa: E402

from agents import escalation_crew, knowledge_crew, web_crew  # noqa: E402
from tools.ticket_store import save_ticket  # noqa: E402


class SupportState(BaseModel):
    question: str = ""
    interactive: bool = False      # True = terminal asks for details with input()
    answer: str = ""
    sources: list[str] = []
    answered_by: str = ""
    steps: list[str] = []          # what happened, shown in the web app
    needs_manual_entry: bool = False
    ticket_id: int | None = None


def create_ticket(question: str, name: str, email: str, phone: str, details: str) -> tuple[int, str]:
    """STEP 3: store the manual entry, then let the Escalation Agent triage it."""
    ticket_id = save_ticket(name, email, phone, question, details)
    message = escalation_crew(
        ticket_id, question, f"name={name}, email={email}, phone={phone}, details={details}")
    return ticket_id, message


class SupportFlow(Flow[SupportState]):

    # ---------- STEP 1: your content (RAG)
    @start()
    def check_knowledge_base(self):
        self.state.steps.append("Step 1: Searched your knowledge base")
        result = knowledge_crew(self.state.question)
        if result and result.found and result.answer.strip():
            self.state.answer, self.state.sources = result.answer, result.sources
            self.state.answered_by = "Knowledge Base (RAG)"
            self.state.steps.append("Step 1: ✅ Answer found in your content")
        else:
            self.state.steps.append("Step 1: ❌ Not found in your content")

    @router(check_knowledge_base)
    def route_after_kb(self):
        return "answered" if self.state.answer else "try_web"

    # ---------- STEP 2: web
    @listen("try_web")
    def search_web(self):
        self.state.steps.append("Step 2: Searched the web")
        result = web_crew(self.state.question)
        if result and result.found and result.answer.strip():
            self.state.answer, self.state.sources = result.answer, result.sources
            self.state.answered_by = "Web Search"
            self.state.steps.append("Step 2: ✅ Answer found on the web")
        else:
            self.state.steps.append("Step 2: ❌ Not found on the web")

    @router(search_web)
    def route_after_web(self):
        return "answered" if self.state.answer else "manual_entry"

    # ---------- STEP 3: manual entry
    @listen("manual_entry")
    def collect_manual_entry(self):
        self.state.needs_manual_entry = True
        self.state.steps.append("Step 3: Manual entry needed")
        if not self.state.interactive:
            return  # the web app shows a form and calls create_ticket()

        print("\n📝 We couldn't find an answer. Please share your details "
              "and our team will get back to you.")
        name = input("   Your name   : ").strip()
        email = input("   Email       : ").strip()
        phone = input("   Phone       : ").strip()
        details = input("   More details: ").strip()
        self.state.ticket_id, self.state.answer = create_ticket(
            self.state.question, name, email, phone, details)
        self.state.answered_by = "Manual Entry → Escalation Agent"
        print(f"   💾 Saved as ticket #{self.state.ticket_id} in data/support.db")


def run_support(question: str, interactive: bool = False) -> SupportState:
    flow = SupportFlow()
    flow.kickoff(inputs={"question": question, "interactive": interactive})
    return flow.state

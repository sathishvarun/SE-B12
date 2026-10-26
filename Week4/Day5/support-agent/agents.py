"""
The 3 CrewAI agents and their tasks.

  Agent 1  Knowledge Base Agent  -> answers ONLY from your content (RAG)
  Agent 2  Web Research Agent    -> answers from the web / your website
  Agent 3  Escalation Agent      -> summarises the manual entry and prioritises it
"""
import os

from crewai import LLM, Agent, Crew, Process, Task
from crewai_tools import ScrapeWebsiteTool, SerperDevTool
from pydantic import BaseModel, Field

from tools.rag_tool import KnowledgeBaseSearchTool
from tools.ticket_store import UpdateTicketTool

VERBOSE = os.getenv("VERBOSE", "false").lower() == "true"


def _llm() -> LLM:
    return LLM(model=os.getenv("MODEL", "gpt-4o-mini"), temperature=0.1)


class AnswerResult(BaseModel):
    """Structured output so Python (not guesswork) decides the next step."""
    found: bool = Field(..., description="True only if a reliable answer was found")
    answer: str = Field(..., description="Customer-ready answer, or empty if not found")
    sources: list[str] = Field(default_factory=list, description="Files or URLs used")


# ---------------------------------------------------------------- Agent 1: RAG
def knowledge_crew(question: str) -> AnswerResult:
    agent = Agent(
        role="Knowledge Base Support Agent",
        goal="Answer customer questions using ONLY the company's own support content.",
        backstory=(
            "You are a careful support specialist. You never guess. If the knowledge "
            "base does not clearly contain the answer, you say it was not found."
        ),
        tools=[KnowledgeBaseSearchTool()],
        llm=_llm(), verbose=VERBOSE, allow_delegation=False,
    )
    task = Task(
        description=(
            "Customer question: {question}\n\n"
            "1. Search the knowledge base with the knowledge_base_search tool "
            "(try 1-2 different phrasings).\n"
            "2. If the passages clearly answer the question, write a short, friendly answer "
            "and set found=true with the source file names.\n"
            "3. If the tool returns NO_MATCH or the passages do not answer it, set found=false "
            "and leave answer empty. Do NOT use outside knowledge."
        ),
        expected_output="AnswerResult JSON",
        output_pydantic=AnswerResult,
        agent=agent,
    )
    out = Crew(agents=[agent], tasks=[task], process=Process.sequential,
               verbose=VERBOSE).kickoff(inputs={"question": question})
    return out.pydantic


# ---------------------------------------------------------------- Agent 2: Web
def web_crew(question: str) -> AnswerResult:
    domain = os.getenv("COMPANY_DOMAIN", "").strip()
    scope = (f"Only trust results from the website {domain}. Prefix every search with "
             f"'site:{domain} '." if domain else "Prefer official and reputable sources.")
    agent = Agent(
        role="Web Research Support Agent",
        goal="Find an accurate answer to the customer's question on the web.",
        backstory="You are an expert researcher who verifies facts before answering customers.",
        tools=[SerperDevTool(n_results=5), ScrapeWebsiteTool()],
        llm=_llm(), verbose=VERBOSE, allow_delegation=False, max_iter=6,
    )
    task = Task(
        description=(
            "The company knowledge base did NOT have this answer.\n"
            "Customer question: {question}\n\n"
            f"{scope}\n"
            "1. Search the web. Open (scrape) the best 1-2 pages if the snippet is not enough.\n"
            "2. If you find a reliable answer, write it simply for the customer, set found=true "
            "and list the URLs in sources.\n"
            "3. If nothing reliable is found, set found=false and leave answer empty."
        ),
        expected_output="AnswerResult JSON",
        output_pydantic=AnswerResult,
        agent=agent,
    )
    out = Crew(agents=[agent], tasks=[task], process=Process.sequential,
               verbose=VERBOSE).kickoff(inputs={"question": question})
    return out.pydantic


# ---------------------------------------------------------- Agent 3: Escalation
def escalation_crew(ticket_id: int, question: str, details: str) -> str:
    agent = Agent(
        role="Support Escalation Agent",
        goal="Turn a customer's manual request into a clear, prioritised support ticket.",
        backstory="You triage support tickets so the human team can act on them quickly.",
        tools=[UpdateTicketTool()],
        llm=_llm(), verbose=VERBOSE, allow_delegation=False,
    )
    task = Task(
        description=(
            "Ticket #{ticket_id} was saved because no answer was found in the knowledge base "
            "or on the web.\nQuestion: {question}\nCustomer details: {details}\n\n"
            "1. Write a one-paragraph summary of the issue and choose a priority "
            "(HIGH = blocked / payment / security, MEDIUM = normal, LOW = general info).\n"
            "2. Save both with the update_support_ticket tool.\n"
            "3. Return a short, polite message to the customer confirming the ticket number "
            "and that the team will contact them."
        ),
        expected_output="A 2-3 sentence confirmation message for the customer.",
        agent=agent,
    )
    out = Crew(agents=[agent], tasks=[task], verbose=VERBOSE).kickoff(
        inputs={"ticket_id": ticket_id, "question": question, "details": details})
    return out.raw

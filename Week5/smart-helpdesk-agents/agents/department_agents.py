"""SUB-AGENTS: one knowledge agent per department (Marketing, Sales, HR, IT, Finance, Support).

Each department agent can only search its own folder in knowledge_base/,
so Marketing answers from marketing docs, HR from HR docs, and so on.
"""
from autogen_agentchat.agents import AssistantAgent

from config import DEPARTMENT_LABELS, DEPARTMENTS, REPLY_LANGUAGE, SERPAPI_API_KEY
from tools.kb_search import format_results, search
from tools.web_search import serpapi_search


def create_department_agent(department: str, model_client, ctx: dict) -> AssistantAgent:
    label = DEPARTMENT_LABELS[department]

    def search_kb(query: str) -> str:
        """Search this department's company documents. Returns passages with their source file."""
        results = search(query, department)
        if not results:  # maybe the router picked a neighbouring team: try all documents
            results = search(query)
        ctx.setdefault("searched_sources", set()).update(r["source"] for r in results)
        return format_results(results)

    tools = [search_kb]
    web_line = ""
    if SERPAPI_API_KEY:
        def web_search(query: str) -> str:
            """Search the public web (SerpAPI). Use ONLY for public/market facts, never for company policy."""
            result = serpapi_search(query)
            ctx.setdefault("searched_sources", set()).add("web")
            return result

        tools.append(web_search)
        web_line = ("\n- You may call web_search for public, non-policy facts (market trends, public holidays, "
                    "software versions). Never use it for company policy.")

    system_message = f"""You are the {label} Knowledge Agent. You handle: {DEPARTMENTS[department]}.
Steps:
1. Call search_kb with the key words from the ticket summary.{web_line}
2. Read the passages. Keep ONLY the ones that really answer the question.
3. Reply in this exact format:
FACTS:
- <fact copied from the documents>
- <fact>
SOURCES: <comma separated file names, e.g. {department}/policy.md> or NONE
If nothing relevant was found write "FACTS: none" and "SOURCES: NONE". Never invent facts.
Write in {REPLY_LANGUAGE} only."""

    return AssistantAgent(
        name=f"{label.replace(' ', '_')}_Agent",
        description=f"{label} department agent that finds answers in the {label} documents.",
        model_client=model_client,
        tools=tools,
        system_message=system_message,
        reflect_on_tool_use=True,
        max_tool_iterations=2,
    )

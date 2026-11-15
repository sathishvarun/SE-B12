"""CrewAI "news desk": two agents turn the newest knowledge-base items into a bilingual digest.

  Researcher  -> picks what changed and why it matters (only from the given items)
  Editor      -> writes the digest in English and Tamil, keeping every source link

The result is saved to data/news_digest.json and shown on the News page.
Without an LLM key (or if CrewAI is not installed) a plain list of the latest items is saved instead.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

from app.config import settings
from app.rag.knowledge import kb

DIGEST = settings.data_dir / "news_digest.json"


def _items_text(docs) -> str:
    return "\n\n".join(f"- {d.metadata['published']} | {d.metadata['title']} | {d.metadata['url']}\n  {d.page_content[:700]}"
                       for d in docs)


def _fallback(docs) -> dict:
    lines = [f"- **{d.metadata['published']}** — {d.metadata['title']} ([source]({d.metadata['url']}))" for d in docs]
    body = "\n".join(lines)
    return {"english": body, "tamil": body, "engine": "list"}


def run_crew(n: int = 8) -> dict:
    docs = kb.latest(n)
    result: dict
    if not settings.has_llm or not docs:
        result = _fallback(docs)
    else:
        try:
            from crewai import LLM, Agent, Crew, Process, Task
            llm = LLM(model=f"openai/{settings.llm_model}", api_key=settings.openai_api_key or "ollama",
                      base_url=settings.openai_base_url or None, temperature=0.2)
            researcher = Agent(role="Beldex news researcher",
                               goal="Find what changed in the Beldex ecosystem using only the items given",
                               backstory="You check facts carefully and never add information that is not in the items.",
                               llm=llm, allow_delegation=False, verbose=False)
            editor = Agent(role="Bilingual editor (English and Tamil)",
                           goal="Write a short, clear news digest in English and in Tamil",
                           backstory="You write for everyday crypto users in Tamil Nadu. Plain words, no hype, no price advice.",
                           llm=llm, allow_delegation=False, verbose=False)
            t1 = Task(description="Items:\n" + _items_text(docs) + "\n\nList the 5 most important updates, newest first. "
                      "For each: date, one-line summary, why it matters, source URL. Use only these items.",
                      expected_output="5 bullet points with date, summary, why it matters and source URL", agent=researcher)
            t2 = Task(description="Turn the research into a digest. Return JSON with keys \"english\" and \"tamil\". "
                      "Each value is markdown bullets: **date** — summary ([source](url)). Keep product names in English.",
                      expected_output='{"english": "...", "tamil": "..."}', agent=editor, context=[t1])
            out = str(Crew(agents=[researcher, editor], tasks=[t1, t2], process=Process.sequential).kickoff())
            out = out[out.find("{"): out.rfind("}") + 1]
            data = json.loads(out)
            result = {"english": data["english"], "tamil": data["tamil"], "engine": "crewai"}
        except Exception as exc:
            print(f"[news_crew] falling back to plain list: {exc}")
            result = _fallback(docs)
    result["generated_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    result["items"] = [{"title": d.metadata["title"], "url": d.metadata["url"], "published": d.metadata["published"],
                        "summary": d.page_content[:260]} for d in docs]
    _add_tamil_titles(result)
    DIGEST.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def _add_tamil_titles(result: dict) -> bool:
    items = result.get("items") or []
    if not items or all(it.get("title_ta") for it in items):
        return False
    from app.translate import ta_titles
    m = ta_titles([it["title"] for it in items])
    for it in items:
        it["title_ta"] = m.get(it["title"], it["title"])
    return True


def load_digest() -> dict:
    if DIGEST.exists():
        data = json.loads(DIGEST.read_text(encoding="utf-8"))
        if settings.has_llm and _add_tamil_titles(data):  # digests made before Tamil titles existed
            DIGEST.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        return data
    return run_crew()


if __name__ == "__main__":
    print(json.dumps(run_crew(), ensure_ascii=False, indent=2)[:2000])

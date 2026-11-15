"""The Beldex agent: question -> (translate) -> retrieve -> grounded answer with numbered sources.

It answers ONLY from the knowledge base. If the answer is not there it says so instead of guessing.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from langchain_core.prompts import ChatPromptTemplate

from app.config import settings
from app.rag.knowledge import Hit, kb
from app.rag.llm import get_llm, token_usage

TAMIL = re.compile(r"[஀-௿]")

NOT_FOUND = {
    "en": "I couldn't find this in the Beldex knowledge base, so I won't guess. "
          "Try asking about BDX, masternodes, BChat, BelNet, BNS, the Beldex Browser or recent updates.",
    "ta": "இந்த தகவல் Beldex அறிவுத் தளத்தில் இல்லை, அதனால் ஊகித்து சொல்ல மாட்டேன். "
          "BDX, masternodes, BChat, BelNet, BNS, Beldex Browser அல்லது சமீபத்திய அப்டேட்ஸ் பற்றி கேளுங்கள்.",
}

ANSWER_PROMPT = ChatPromptTemplate.from_messages([
    ("system",
     "You are BDX Insight, an assistant that explains the Beldex (BDX) ecosystem.\n"
     "Rules:\n"
     "1. Use ONLY the numbered context passages. Never use outside knowledge.\n"
     "2. Put the passage number after each fact, like [1] or [2][3].\n"
     "3. If the context does not answer the question, reply exactly: NOT_IN_KB\n"
     "4. No price predictions and no investment advice.\n"
     "5. Write the whole answer in {language}. Keep product names (BDX, BChat, BelNet, BNS) in English.\n"
     "6. Be clear and short: a direct answer first, then up to 4 bullet points."),
    ("human", "Context:\n{context}\n\nQuestion: {question}"),
])

TRANSLATE_PROMPT = ChatPromptTemplate.from_messages([
    ("system", "Translate the user's question to English for a search engine. Reply with the translation only."),
    ("human", "{question}"),
])


@dataclass
class Answer:
    text: str
    lang: str
    sources: list[dict] = field(default_factory=list)
    found: bool = True
    mode: str = "llm"
    steps: list[str] = field(default_factory=list)
    prompt_tokens: int = 0
    completion_tokens: int = 0

    @property
    def cost_usd(self) -> float:
        return round(self.prompt_tokens / 1e6 * settings.price_in_per_m
                     + self.completion_tokens / 1e6 * settings.price_out_per_m, 6)


def _sources(hits: list[Hit]) -> list[dict]:
    out = []
    for i, h in enumerate(hits, 1):
        m = h.doc.metadata
        out.append({"n": i, "title": m["title"], "url": m["url"], "published": m.get("published", ""),
                    "kind": m.get("kind", ""), "snippet": h.doc.page_content[:280].strip(),
                    "score": round(h.score, 3)})
    return out


def ask(question: str, lang: str = "en") -> Answer:
    lang = "ta" if lang == "ta" else "en"
    ans = Answer(text="", lang=lang)
    llm = get_llm()
    query = question

    if TAMIL.search(question) and llm is not None:
        msg = (TRANSLATE_PROMPT | llm).invoke({"question": question})
        query = f"{question}\n{msg.content}"
        p, c = token_usage(msg)
        ans.prompt_tokens += p
        ans.completion_tokens += c
        ans.steps.append(f"Translated the question for search: “{msg.content.strip()[:80]}”")

    hits = kb.search(query, k=5)
    pages = len({h.doc.metadata['url'] for h in hits})
    ans.steps.append(f"Searched the knowledge base ({kb.backend}): {len(hits)} passages from {pages} sources")
    if not hits:
        ans.text, ans.found, ans.mode = NOT_FOUND[lang], False, "none"
        return ans
    ans.sources = _sources(hits)

    if llm is None:  # no API key: show the best passages, still with sources
        ans.mode = "extractive"
        head = ("AI model is not configured, so here are the most relevant passages:" if lang == "en"
                else "AI மாடல் அமைக்கப்படவில்லை; தொடர்புடைய பகுதிகள் கீழே (ஆங்கிலத்தில்):")
        lines = [f"- {h.doc.page_content[:300].strip()} [{i}]" for i, h in enumerate(hits[:3], 1)]
        ans.text = head + "\n" + "\n".join(lines)
        ans.steps.append("Showed matching passages (no LLM key set)")
        return ans

    context = "\n\n".join(f"[{s['n']}] {s['title']} ({s['url']})\n{h.doc.page_content}"
                          for s, h in zip(ans.sources, hits))
    msg = (ANSWER_PROMPT | llm).invoke({"context": context, "question": question,
                                        "language": "Tamil" if lang == "ta" else "English"})
    p, c = token_usage(msg)
    ans.prompt_tokens += p
    ans.completion_tokens += c
    text = msg.content.strip()
    if "NOT_IN_KB" in text:
        ans.text, ans.found, ans.mode, ans.sources = NOT_FOUND[lang], False, "llm", []
        ans.steps.append("The passages did not answer it, so no answer was made up")
        return ans
    used = {int(n) for n in re.findall(r"\[(\d+)\]", text)}
    if used:
        ans.sources = [s for s in ans.sources if s["n"] in used]
    ans.text = text
    ans.steps.append(f"Wrote the answer in {'Tamil' if lang == 'ta' else 'English'} with {len(ans.sources)} citations")
    return ans

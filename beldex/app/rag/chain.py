"""The Beldex agent: question -> (translate) -> retrieve -> grounded answer with numbered sources.

It answers ONLY from the knowledge base. If the answer is not there it says so instead of guessing.
"""
from __future__ import annotations
import logging

import re
from dataclasses import dataclass, field

from langchain_core.prompts import ChatPromptTemplate

from app.config import settings
from app.rag.knowledge import Hit, kb
from app.rag.llm import get_llm, token_usage

log = logging.getLogger("beldex.chain")

TAMIL = re.compile(r"[஀-௿]")

NOT_FOUND = {
    "en": "I couldn't find this in the Beldex knowledge base, so I won't guess. "
          "Try asking about BDX, masternodes, BChat, BelNet, BNS, the Beldex Browser or recent updates.",
    "ta": "இந்த தகவல் Beldex அறிவுத் தளத்தில் இல்லை, அதனால் ஊகித்து சொல்ல மாட்டேன். "
          "BDX, masternodes, BChat, BelNet, BNS, Beldex Browser அல்லது சமீபத்திய அப்டேட்ஸ் பற்றி கேளுங்கள்.",
}

ANSWER_PROMPT = ChatPromptTemplate.from_messages([
    ("system",
     "You are Beldex AI, an assistant that explains the Beldex (BDX) ecosystem.\n"
     "Rules:\n"
     "1. Use ONLY the numbered context passages. Do not add facts that are not in them.\n"
     "2. Put the passage number after each fact, like [1] or [2][3].\n"
     "3. The passages cover Beldex and general crypto topics (blockchain, Bitcoin, wallets, staking, privacy, "
     "safety). If they answer the question fully or partly, answer what they cover and briefly say what is not "
     "covered. Only if the question has nothing to do with the passages (for example weather or cooking), "
     "reply exactly: NOT_IN_KB\n"
     "4. No price predictions and no investment advice.\n"
     "5. Write the whole answer in {language}. Keep product names (BDX, BChat, BelNet, BNS) in English.\n"
     "6. Format: start with one bold sentence that answers the question directly. Then up to 4 short bullet "
     "points with the key facts (numbers, dates, names). If useful, end with one line starting with "
     "'Why it matters:'.\n"
     "7. On the very last line write FOLLOW_UPS: followed by 3 short follow-up questions in {language} that the "
     "context can answer, separated by ' | '."),
    ("human", "Context:\n{context}\n\nQuestion: {question}"),
])

TRANSLATE_PROMPT = ChatPromptTemplate.from_messages([
    ("system", "Translate the user's question to English for a search engine. Reply with the translation only."),
    ("human", "{question}"),
])


FOLLOW_BANK = {
    "en": {
        "masternode": ["How are masternode rewards paid?", "What happens if a masternode goes offline?"],
        "bns": ["How do I buy a BNS name?", "What is the BNS Marketplace?"],
        "bchat": ["What is BelNet?", "Which BChat version is the latest?"],
        "bridge": ["Am I eligible for the 1:1 swap?", "What is the Privacy Protocol?"],
        "hardfork": ["What is Bulletproofs++?", "What is on the 2026 roadmap?"],
        "exchange": ["Where can I trade BDX?", "What did Grayscale say about BDX?"],
        "_": ["How did Beldex start?", "What is new in 2026?", "What do I need to run a masternode?"],
    },
    "ta": {
        "masternode": ["Masternode வெகுமதிகள் எப்படி கிடைக்கும்?", "Masternode offline ஆனால் என்ன ஆகும்?"],
        "bns": ["BNS பெயரை எப்படி வாங்குவது?", "BNS Marketplace என்றால் என்ன?"],
        "bchat": ["BelNet என்றால் என்ன?", "BChat-இன் சமீபத்திய version எது?"],
        "bridge": ["1:1 swap-க்கு நான் தகுதியானவனா?", "Privacy Protocol என்றால் என்ன?"],
        "hardfork": ["Bulletproofs++ என்றால் என்ன?", "2026 roadmap-இல் என்ன உள்ளது?"],
        "exchange": ["BDX-ஐ எங்கே trade செய்யலாம்?", "Grayscale BDX பற்றி என்ன சொன்னது?"],
        "_": ["பெல்டெக்ஸ் எப்படி தொடங்கியது?", "2026-இல் என்ன புதுசு?", "Masternode இயக்க என்ன தேவை?"],
    },
}


def _bank_follow_ups(text: str, lang: str, asked: str) -> list[str]:
    bank, low, out = FOLLOW_BANK[lang], text.lower(), []
    for key in ("masternode", "bns", "bchat", "bridge", "hardfork", "exchange"):
        if key in low or (key == "hardfork" and "obscura" in low) or (key == "exchange" and "kraken" in low):
            out += bank[key]
    out += bank["_"]
    return [q for q in dict.fromkeys(out) if q.lower() != asked.lower()][:3]


@dataclass
class Answer:
    text: str
    lang: str
    sources: list[dict] = field(default_factory=list)
    found: bool = True
    mode: str = "llm"
    steps: list[str] = field(default_factory=list)
    follow_ups: list[str] = field(default_factory=list)
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


def _extractive(ans: "Answer", hits, lang: str, question: str) -> "Answer":
    ans.mode = "extractive"
    head = ("The AI model is not available right now, so here are the most relevant passages:" if lang == "en"
            else "AI மாடல் இப்போது கிடைக்கவில்லை; தொடர்புடைய பகுதிகள் கீழே (ஆங்கிலத்தில்):")
    lines = [f"- {h.doc.page_content[:300].strip()} [{i}]" for i, h in enumerate(hits[:3], 1)]
    ans.text = head + "\n" + "\n".join(lines)
    ans.steps.append("Showed matching passages (AI model not available)")
    ans.follow_ups = _bank_follow_ups(" ".join(h.doc.page_content for h in hits), lang, question)
    return ans


def ask(question: str, lang: str = "en") -> Answer:
    lang = "ta" if lang == "ta" else "en"
    ans = Answer(text="", lang=lang)
    llm = get_llm()
    query = question

    if TAMIL.search(question) and llm is not None:
        try:
            msg = (TRANSLATE_PROMPT | llm).invoke({"question": question})
            query = f"{question}\n{msg.content}"
            p, c = token_usage(msg)
            ans.prompt_tokens += p
            ans.completion_tokens += c
            ans.steps.append(f"Translated the question for search: “{msg.content.strip()[:80]}”")
        except Exception as e:  # bad key, quota or network: keep going with the original question
            log.warning("translate failed: %s", e)
            llm = None

    hits = kb.search(query, k=6)
    pages = len({h.doc.metadata['url'] for h in hits})
    ans.steps.append(f"Searched the knowledge base ({kb.backend}): {len(hits)} passages from {pages} sources")
    if not hits:
        ans.text, ans.found, ans.mode = NOT_FOUND[lang], False, "none"
        ans.follow_ups = FOLLOW_BANK[lang]["_"]
        return ans
    ans.sources = _sources(hits)

    if llm is None:  # no API key: show the best passages, still with sources
        return _extractive(ans, hits, lang, question)

    context = "\n\n".join(f"[{s['n']}] {s['title']} ({s['url']})\n{h.doc.page_content}"
                          for s, h in zip(ans.sources, hits))
    try:
        msg = (ANSWER_PROMPT | llm).invoke({"context": context, "question": question,
                                            "language": "Tamil" if lang == "ta" else "English"})
    except Exception as e:  # bad key, quota or network: still answer with the passages
        log.warning("answer failed: %s", e)
        return _extractive(ans, hits, lang, question)
    p, c = token_usage(msg)
    ans.prompt_tokens += p
    ans.completion_tokens += c
    text = msg.content.strip()
    m = re.search(r"\n?\s*FOLLOW_UPS:\s*(.+)\s*$", text)
    if m:
        ans.follow_ups = [q.strip(" -•*") for q in m.group(1).split("|") if q.strip()][:3]
        text = text[:m.start()].rstrip()
    if not ans.follow_ups:
        ans.follow_ups = _bank_follow_ups(text, lang, question)
    if "NOT_IN_KB" in text:
        ans.follow_ups = FOLLOW_BANK[lang]["_"]
        ans.text, ans.found, ans.mode, ans.sources = NOT_FOUND[lang], False, "llm", []
        ans.steps.append("The passages did not answer it, so no answer was made up")
        return ans
    used = {int(n) for n in re.findall(r"\[(\d+)\]", text)}
    if used:
        ans.sources = [s for s in ans.sources if s["n"] in used]
    ans.text = text
    ans.steps.append(f"Wrote the answer in {'Tamil' if lang == 'ta' else 'English'} with {len(ans.sources)} citations")
    return ans

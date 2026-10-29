"""
cli_test.py
-----------
Quick terminal test of the multi-agent engine (no Streamlit needed).
Run:  python cli_test.py
Use this first to confirm your OpenAI key and AutoGen install work.
"""

import asyncio

from agents import SupportOrchestrator, TraceEvent


def show(ev: TraceEvent) -> None:
    arrow = f" -> {ev.target}" if ev.target else ""
    print(f"[{ev.t:>5.2f}s] {ev.actor:<16} {ev.kind:<12}{arrow:<16} {ev.detail[:90]}")


async def main() -> None:
    bot = SupportOrchestrator(on_event=show)
    question = "My VPN is slow and I also want to know my leave balance. My ID is EMP1001."
    print(f"\nQUESTION: {question}\n")
    result = await bot.ask(question)
    print("\n" + "=" * 70 + "\nFINAL ANSWER\n" + "=" * 70)
    print(result.answer)
    print(f"\nDepartments: {result.departments} | Tickets: {len(result.tickets)} | "
          f"Tokens: {sum(result.tokens.values())} | Time: {result.latency}s")


if __name__ == "__main__":
    asyncio.run(main())

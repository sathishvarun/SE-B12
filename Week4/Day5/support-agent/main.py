"""
Terminal version of the Customer Support Agent.
For the web version on localhost, run:  streamlit run app.py

Run:  python main.py
"""
from support_flow import run_support


def main():
    print("Customer Support Agent  (type 'exit' to quit)")
    while True:
        question = input("\n💬 Customer question: ").strip()
        if question.lower() in {"exit", "quit", ""}:
            break
        state = run_support(question, interactive=True)
        print("\n" + "=" * 60)
        print(f"🤖 Answered by: {state.answered_by}")
        print("-" * 60)
        print(state.answer)
        if state.sources:
            print("\nSources: " + ", ".join(state.sources))
        print("=" * 60)


if __name__ == "__main__":
    main()

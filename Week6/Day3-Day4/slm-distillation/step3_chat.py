"""
STEP 3 - Chat with the trained student in the terminal.

Run:            python step3_chat.py
Before/after:   python step3_chat.py --compare
Type 'exit' to quit.
"""
import argparse

from inference import StudentModel, load_untrained_student


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--compare", action="store_true",
                        help="also show the untrained student's answer")
    args = parser.parse_args()

    print("Loading distilled student...")
    student = StudentModel()
    base = load_untrained_student() if args.compare else None
    print(f"Ready on {student.device}. Type a question (or 'exit').\n")

    while True:
        try:
            q = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not q:
            continue
        if q.lower() in {"exit", "quit"}:
            break
        if base:
            print(f"\n[Before distillation]: {base.generate(q)}")
        print(f"\n[Distilled student]:   {student.generate(q)}\n")


if __name__ == "__main__":
    main()


import json
from pathlib import Path

INPUT_FILE = Path("adapter_comparison_results.json")
OUTPUT_FILE = Path("adapter_evaluation_report.md")

if not INPUT_FILE.exists():
    raise FileNotFoundError(f"Missing file: {INPUT_FILE}")

with INPUT_FILE.open("r", encoding="utf-8") as f:
    results = json.load(f)

if not results:
    raise ValueError("No comparison results found.")

report = []

report.append("# Marketing AI Assistant – V1 vs V2 Evaluation")
report.append("")
report.append(f"Total questions evaluated: {len(results)}")
report.append("")

report.append(
    "| Category | Question | V1 length | V2 length |"
)
report.append("|---|---|---:|---:|")

for item in results:
    report.append(
        f"| {item.get('category', 'General')} "
        f"| {item['question']} "
        f"| {len(item.get('v1_answer', ''))} "
        f"| {len(item.get('v2_answer', ''))} |"
    )

for index, item in enumerate(results, start=1):
    report.append("")
    report.append(f"## Question {index}: {item.get('category', 'General')}")
    report.append("")
    report.append(f"**Question:** {item['question']}")
    report.append("")
    report.append("### V1 Answer")
    report.append(item.get("v1_answer", "No answer"))
    report.append("")
    report.append("### V2 Answer")
    report.append(item.get("v2_answer", "No answer"))
    report.append("")
    report.append("---")

OUTPUT_FILE.write_text("\n".join(report), encoding="utf-8")

print("Evaluation report created successfully.")
print("Questions evaluated:", len(results))
print("Report:", OUTPUT_FILE)

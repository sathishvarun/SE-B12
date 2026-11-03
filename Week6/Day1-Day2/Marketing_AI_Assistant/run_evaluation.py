
import json
import os
import requests
from pathlib import Path
from dotenv import load_dotenv

PROJECT_DIR = Path(__file__).resolve().parent

load_dotenv(PROJECT_DIR / ".env")

API_KEY = os.getenv("MARKETING_API_KEY")
API_URL = "http://127.0.0.1:8000/generate"

if not API_KEY:
    raise RuntimeError("MARKETING_API_KEY not found in .env")

with open(PROJECT_DIR / "evaluation_questions.json", "r") as file:
    questions = json.load(file)

results = []

headers = {
    "X-API-Key": API_KEY,
    "Content-Type": "application/json"
}

for item in questions:
    print(f"\nTesting: {item['category']}")

    payload = {
        "question": item["question"],
        "max_new_tokens": 200
    }

    try:
        response = requests.post(
            API_URL,
            json=payload,
            headers=headers,
            timeout=180
        )

        response.raise_for_status()
        answer = response.json()["answer"]

        results.append({
            "category": item["category"],
            "question": item["question"],
            "answer": answer,
            "status": "Success"
        })

        print("Status: Success")
        print("Answer:", answer)

    except requests.RequestException as error:
        results.append({
            "category": item["category"],
            "question": item["question"],
            "answer": "",
            "status": "Failed",
            "error": str(error)
        })

        print("Status: Failed")
        print(error)

output_file = PROJECT_DIR / "evaluation_results.json"

with open(output_file, "w") as file:
    json.dump(results, file, indent=4, ensure_ascii=False)

print("\nEvaluation completed.")
print(f"Results saved to: {output_file}")

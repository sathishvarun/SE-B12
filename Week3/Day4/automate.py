from openai import OpenAI

# Initialize the client with your OpenAI API key
client = OpenAI(api_key="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")

# Sample data to automate
customer_feedbacks = [
    "The delivery arrived 4 days late and the box was completely damaged!",
    "Absolutely loved the onboarding experience, super smooth and intuitive.",
    "The software works fine, but the pricing is slightly on the higher side."
]

def analyze_and_respond(feedback_text):
    prompt = f"""
    Analyze the following customer review:
    "{feedback_text}"

    Provide:
    1. Sentiment (Positive / Negative / Neutral)
    2. A polite, professional 2-sentence response draft to send to the customer.
    """
    
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "user", "content": prompt}
        ]
    )
    return response.choices[0].message.content

# Run automation loop
print("--- Starting Automation Task ---\n")
for index, feedback in enumerate(customer_feedbacks, start=1):
    print(f"[{index}] Processing Feedback: {feedback}")
    result = analyze_and_respond(feedback)
    print("AI Analysis & Draft:")
    print(result.strip())
    print("-" * 50)
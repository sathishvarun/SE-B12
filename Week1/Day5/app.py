from transformers import pipeline

sentiment = pipeline(
    "sentiment-analysis",
    model="./my_model",
    tokenizer="./my_model"
)

#text = "I really like learning Generative AI."
text = "What is python?"
result = sentiment(text)

print(result)
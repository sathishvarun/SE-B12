from transformers import AutoTokenizer, AutoModelForSequenceClassification

model_name = "distilbert-base-uncased-finetuned-sst-2-english"

print("Downloading model...")

tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForSequenceClassification.from_pretrained(model_name)

tokenizer.save_pretrained("./my_model")
model.save_pretrained("./my_model")

print("Model downloaded successfully!")
print("Saved in: ./my_model")
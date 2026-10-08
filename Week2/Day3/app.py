import os

from dotenv import load_dotenv
from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_chroma import Chroma


# Load .env
load_dotenv()

if not os.getenv("OPENAI_API_KEY"):
    raise ValueError("OPENAI_API_KEY is missing")


# -----------------------------
# 1. DATA INGESTION
# -----------------------------

print("1. Loading document...")

loader = TextLoader("data/sample.txt")
documents = loader.load()

print(f"   Documents loaded: {len(documents)}")


# -----------------------------
# 2. TEXT SPLITTER
# -----------------------------

print("2. Splitting document...")

text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=300,
    chunk_overlap=50
)

chunks = text_splitter.split_documents(documents)

print(f"   Chunks created: {len(chunks)}")


# -----------------------------
# 3. EMBEDDINGS
# -----------------------------

print("3. Creating embeddings...")

embeddings = OpenAIEmbeddings(
    model="text-embedding-3-small"
)


# -----------------------------
# 4. VECTOR STORE
# -----------------------------

print("4. Creating vector store...")

vector_store = Chroma.from_documents(
    documents=chunks,
    embedding=embeddings,
    collection_name="rag_demo"
)

print("   Vector store created successfully")


# -----------------------------
# 5. RETRIEVER
# -----------------------------

print("5. Creating retriever...")

retriever = vector_store.as_retriever(
    search_kwargs={"k": 3}
)

print("   Retriever created successfully")


# -----------------------------
# 6. ASK QUESTION
# -----------------------------

question = input("\nAsk a question: ")

print("\n6. Searching relevant information...")

results = retriever.invoke(question)


# -----------------------------
# 7. DISPLAY RETRIEVED DATA
# -----------------------------

print("\n==============================")
print("RETRIEVED INFORMATION")
print("==============================")

for i, document in enumerate(results, start=1):
    print(f"\n--- Result {i} ---")
    print(document.page_content)


# -----------------------------
# 8. LLM
# -----------------------------

print("\n7. Sending information to OpenAI...")

llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0
)


# -----------------------------
# 9. GENERATE ANSWER
# -----------------------------

context = "\n\n".join(
    document.page_content
    for document in results
)

prompt = f"""
Answer the question using ONLY the information provided below.

Context:
{context}

Question:
{question}

If the answer is not available in the context, say:
"I don't know based on the provided document."
"""

response = llm.invoke(prompt)


# -----------------------------
# 10. FINAL ANSWER
# -----------------------------

print("\n==============================")
print("FINAL ANSWER")
print("==============================")

print(response.content)
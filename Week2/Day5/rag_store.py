# rag_store.py
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma
from mock_data import CATEGORIES_DATA

def generate_documents():
    documents = []
    for category, items in CATEGORIES_DATA.items():
        for item_name, brands in items.items():
            for brand_entry in brands:
                brand = brand_entry["brand"]
                for size in brand_entry["sizes"]:
                    pack = size["pack"]
                    price = size["price"]
                    stock = size["stock"]
                    status = "In Stock" if stock > 0 else "Out of Stock"
                    
                    content = (
                        f"Item: {item_name}\n"
                        f"Brand: {brand}\n"
                        f"Category: {category}\n"
                        f"Size/Weight: {pack}\n"
                        f"Price: ₹{price:.2f}\n"
                        f"Stock Status: {status} ({stock} units available)"
                    )
                    
                    doc = Document(
                        page_content=content,
                        metadata={
                            "category": category,
                            "item": item_name,
                            "brand": brand,
                            "price": price,
                            "pack": pack
                        }
                    )
                    documents.append(doc)
    return documents

def init_vector_store():
    documents = generate_documents()
    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
    
    vector_store = Chroma.from_documents(
        documents=documents,
        embedding=embeddings,
        collection_name="sk_mini_mart_brands"
    )
    # k=6 allows returning multiple brand alternatives
    return vector_store.as_retriever(search_kwargs={"k": 6})
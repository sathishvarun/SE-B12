import os
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

# --- PURPOSE: Modern LangChain Ingestion Imports ---
from langchain_core.documents import Document
from langchain_community.document_loaders import TextLoader
from langchain_openai import ChatOpenAI
from langchain_neo4j import Neo4jGraph
from langchain_experimental.graph_transformers import LLMGraphTransformer

# Load environment credentials (.env)
load_dotenv()

# --- PURPOSE: Web Scraper Document Loader ---
# Fetches Tamil Nadu Agriculture Department scheme listing and wraps into a Document
def load_tn_schemes(url: str):
    response = requests.get(url, timeout=15)
    response.raise_for_status()
    
    soup = BeautifulSoup(response.text, "html.parser")
    schemes_text = []
    
    tables = soup.find_all("table")
    if tables:
        for row in tables[0].find_all("tr"):
            cols = [col.get_text(strip=True) for col in row.find_all(["td", "th"])]
            if cols:
                schemes_text.append(" | ".join(cols))
    else:
        schemes_text.append(soup.get_text(separator="\n", strip=True))

    full_text = "\n".join(schemes_text[:50])
    
    return [
        Document(
            page_content=full_text,
            metadata={"source": url, "department": "Agriculture and Farmers Welfare"}
        )
    ]

# 1. Load Web Data
source_url = "https://www.tn.gov.in/scheme_list.php?dep_id=Mg=="
web_docs = load_tn_schemes(source_url)
print(f"[✓] Scraped web document length: {len(web_docs[0].page_content)} characters.")

# 2. Load Local Text File Data
# --- PURPOSE: Local Document Loader ---
# Reads unstructured scheme notes directly from local storage.
text_file_path = "local_schemes.txt"
if os.path.exists(text_file_path):
    txt_loader = TextLoader(text_file_path, encoding="utf-8")
    txt_docs = txt_loader.load()
    print(f"[✓] Loaded local text file: {len(txt_docs[0].page_content)} characters.")
else:
    txt_docs = []
    print(f"[!] Warning: {text_file_path} not found. Skipping file ingestion.")

# Combine both document streams
all_documents = web_docs + txt_docs
print(f"[✓] Total documents ready for transformation: {len(all_documents)}")

# 3. Connect to Neo4j Instance
graph = Neo4jGraph(
    url=os.getenv("NEO4J_URI"),
    username=os.getenv("NEO4J_USERNAME"),
    password=os.getenv("NEO4J_PASSWORD"),
    database=os.getenv("NEO4J_DATABASE", "neo4j")
)

# 4. Define Graph Schema & Model
llm = ChatOpenAI(temperature=0, model_name="gpt-4o-mini")

allowed_nodes = ["Scheme", "Beneficiary", "Benefit", "Eligibility", "Department"]
allowed_relationships = [
    "OFFERED_BY",
    "TARGETS_BENEFICIARY",
    "PROVIDES_BENEFIT",
    "REQUIRES_CRITERIA"
]

llm_transformer = LLMGraphTransformer(
    llm=llm,
    allowed_nodes=allowed_nodes,
    allowed_relationships=allowed_relationships
)

# 5. Extract Triples (Nodes and Edges)
print("[*] Extracting graph entities and relationships via LLM...")
graph_documents = llm_transformer.convert_to_graph_documents(all_documents)

total_nodes = sum(len(doc.nodes) for doc in graph_documents)
total_relations = sum(len(doc.relationships) for doc in graph_documents)
print(f"[✓] Extracted total {total_nodes} nodes and {total_relations} relationships.")

# 6. Save directly into Neo4j
graph.add_graph_documents(
    graph_documents,
    baseEntityLabel=True,
    include_source=True
)

graph.refresh_schema()
print("[✓] All web and text file records successfully committed to Neo4j!")
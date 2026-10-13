import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_neo4j import Neo4jGraph, GraphCypherQAChain

load_dotenv()

# --- PURPOSE: Neo4j Connection ---
graph = Neo4jGraph(
    url=os.getenv("NEO4J_URI"),
    username=os.getenv("NEO4J_USERNAME"),
    password=os.getenv("NEO4J_PASSWORD"),
    database=os.getenv("NEO4J_DATABASE", "neo4j")
)

graph.refresh_schema()

llm = ChatOpenAI(temperature=0, model_name="gpt-4o-mini")

# --- PURPOSE: Query Pipeline with Visible Intermediate Steps ---
# return_intermediate_steps=True captures the Cypher statement before execution
cypher_chain = GraphCypherQAChain.from_llm(
    llm=llm,
    graph=graph,
    verbose=True,
    return_intermediate_steps=True,
    allow_dangerous_requests=True
)

# Test query that touches both text file data and scraped web data
query = "What benefits are provided for solar pump sets and farmer welfare schemes?"

print("\n" + "=" * 55)
print(f"User Query: {query}")
print("=" * 55)

response = cypher_chain.invoke({"query": query})

# Extract steps
generated_cypher = response["intermediate_steps"][0]["query"]
database_context = response["intermediate_steps"][1]["context"]

print("\n[1] GENERATED CYPHER QUERY:")
print(generated_cypher)

print("\n[2] RETRIEVED GRAPH CONTEXT FROM NEO4J:")
print(database_context)

print("\n[3] FINAL GROUNDED ANSWER:")
print(response["result"])
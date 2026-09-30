import os
import chromadb
from chromadb.utils import embedding_functions
from google import genai
from google.genai import types

# ==========================================
# 1. SETUP VECTOR STORE & EMBEDDINGS (Local)
# ==========================================
client = chromadb.Client()

# Local embedding model for fast, cost-free retrieval
embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name="all-MiniLM-L6-v2"
)

collection = client.create_collection(
    name="company_knowledge_base",
    embedding_function=embedding_fn,
    metadata={"hnsw:space": "cosine"}
)

# Ingest sample knowledge base documents
documents = [
    "Project Apollo was initiated in Q1 2024 to modernize the analytics stack using Apache Spark.",
    "Internal code deployments are handled by SkyShip every Tuesday and Thursday at 10:00 AM UTC.",
    "Employees are eligible for a $500 annual home-office stipend after completing their 90-day probationary period.",
    "Travel expense reimbursement reports must be submitted within 14 business days of trip completion."
]

collection.add(
    documents=documents,
    metadatas=[{"dept": "Eng"}, {"dept": "DevOps"}, {"dept": "HR"}, {"dept": "Finance"}],
    ids=["doc_1", "doc_2", "doc_3", "doc_4"]
)

print(f"✓ Ingested {collection.count()} documents into ChromaDB.\n")


# ==========================================
# 2. RETRIEVAL STEP
# ==========================================
def retrieve_relevant_context(query: str, top_k: int = 2) -> list[str]:
    """Queries ChromaDB and returns the most relevant document chunks."""
    results = collection.query(
        query_texts=[query],
        n_results=top_k
    )
    return results["documents"][0]


# ==========================================
# 3. AUGMENTATION STEP
# ==========================================
def build_rag_prompt(query: str, retrieved_chunks: list[str]) -> str:
    """Combines retrieved facts with the user question into a strict prompt."""
    context_block = "\n---\n".join(retrieved_chunks)
    prompt = f"""You are a helpful assistant. Use ONLY the facts provided in the Context below to answer the Question.
If the answer cannot be found in the Context, say "I don't have enough information in the provided knowledge base."

Context:
{context_block}

Question:
{query}

Answer:"""
    return prompt


# ==========================================
# 4. GENERATION STEP (Gemini API)
# ==========================================
# Automatically reads GEMINI_API_KEY from environment variables
ai_client = genai.Client()

def generate_answer_gemini(prompt: str) -> str:
    """Calls Gemini API with low temperature for factual groundness."""
    response = ai_client.models.generate_content(
        model="gemini-3.5-flash",
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=0.0
        )
    )
    return response.text.strip()


# ==========================================
# 5. END-TO-END RAG PIPELINE
# ==========================================
def ask_rag(question: str):
    print(f"Query: '{question}'")
    
    # 1. Retrieve
    chunks = retrieve_relevant_context(question, top_k=2)
    print("  -> Retrieved Chunks:")
    for idx, c in enumerate(chunks, 1):
        print(f"     [{idx}] {c}")
    
    # 2. Augment
    prompt = build_rag_prompt(question, chunks)
    
    # 3. Generate via Gemini API
    answer = generate_answer_gemini(prompt)
    
    print(f"\nFinal Answer: {answer}")
    print("=" * 60 + "\n")


# ==========================================
# 6. RUN TESTS
# ==========================================
if __name__ == "__main__":
    # Test 1: In-domain question
    ask_rag("When can developers deploy code and which tool is used?")
    
    # Test 2: HR policy question
    ask_rag("How much is the home office budget and when do I qualify?")
    
    # Test 3: Out-of-domain question (verifies hallucination resistance)
    ask_rag("What is the capital of Australia?")
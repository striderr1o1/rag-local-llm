# import chromadb
# import logging
# import os
# import logging
# import requests

# OLLAMA_URL = "http://localhost:11434"
# EMBED_MODEL = "mxbai-embed-large"

# def get_embedding(text):
#     url = OLLAMA_URL + "/api/embeddings"
#     payload = {
#         "model": EMBED_MODEL,
#         "prompt": text
#     }
#     response = requests.post(url, json=payload)
#     response.raise_for_status()
#     return response.json()["embedding"]

# class FunctionalEmbedFn:
#     def __call__(self, input):
#         # input is a list of strings
#         return [get_embedding(text) for text in input]
#     def name(self):
#         return "functional_embed_fn"

# embed_fn = FunctionalEmbedFn()


# def simple_chunk_lines(text, chunk_size=3):
#     lines = text.split('\n')
#     chunks = []
#     for i in range(0, len(lines), chunk_size):
#         chunk = '\n'.join(lines[i:i+chunk_size])
#         chunks.append(chunk)
#     return chunks

# schema_text = """
# Table: users (id, name, email)
# Table: orders (id, user_id, amount, date)
# Table: products (id, name, price)
# """

# chunks = simple_chunk_lines(schema_text, chunk_size=1) 

# import chromadb

# client = chromadb.Client()
# collection = client.get_or_create_collection(
    
#     name="sql_docs",
#     embedding_function=embed_fn # You already defined this
# )
# ids = [f"chunk_{i}" for i in range(len(chunks))]
# collection.add(
#     documents=chunks,
#     ids=ids
# )
# user_question = "Show me all orders for user with email 'alice@example.com'"

# results = collection.query(
#     query_texts=[user_question],
#     n_results=3  # You can adjust this number
# )
# # The results['documents'] is a list of lists (one list per query)
# relevant_chunks = results['documents'][0]
# context = "\n".join(relevant_chunks)
# print("Retrieved context:\n", context)

import chromadb
import requests

# Local Ollama and model setup
OLLAMA_URL = "http://localhost:11434"
EMBED_MODEL = "mxbai-embed-large"

def get_embedding(text):
    url = f"{OLLAMA_URL}/api/embeddings"
    payload = {
        "model": EMBED_MODEL,
        "input": text  # Correct key
    }
    response = requests.post(url, json=payload)
    response.raise_for_status()
    return response.json()["embedding"]

class FunctionalEmbedFn:
    def __call__(self, input):
        return [get_embedding(text) for text in input]

    def name(self):
        return "functional_embed_fn"

embed_fn = FunctionalEmbedFn()

def simple_chunk_lines(text, chunk_size=3):
    lines = text.split('\n')
    chunks = []
    for i in range(0, len(lines), chunk_size):
        chunk = '\n'.join(lines[i:i+chunk_size]).strip()
        if chunk:
            chunks.append(chunk)
    return chunks

schema_text = """
Table: users (id, name, email)
Table: orders (id, user_id, amount, date)
Table: products (id, name, price)
"""

chunks = simple_chunk_lines(schema_text, chunk_size=1)

# ✅ Correct New Chroma Client
client = chromadb.PersistentClient(path=".chromadb")  # Local storage
# OR use this for in-memory:
# client = chromadb.EphemeralClient()

collection = client.get_or_create_collection(
    name="sql_docs",
    embedding_function=embed_fn
)

ids = [f"chunk_{i}" for i in range(len(chunks))]
collection.add(
    documents=chunks,
    ids=ids
)

user_question = "Show me all orders for user with email 'alice@example.com'"

results = collection.query(
    query_texts=[user_question],
    n_results=3
)

relevant_chunks = results['documents'][0]
context = "\n".join(relevant_chunks)
print("Retrieved context:\n", context)

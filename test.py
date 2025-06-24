import chromadb
import os
import logging
import requests
import json

schema_text = """
Table: users (id, name, email)
Table: orders (id, user_id, amount, date)
Table: products (id, name, price)
"""
#--------------------------------------------------------------------------------------------------------
#STEP 1: CHUNK DATA

def simple_chunk_lines(text, chunk_size=3):
    lines = text.strip().split('\n')
    chunks = []
    for i in range(0, len(lines), chunk_size):
        chunk = '\n'.join(lines[i:i+chunk_size]).strip()
        if chunk:
            chunks.append(chunk)
    return chunks
#--------------------------------------------------------------------------------------------------------
def get_embedding(text):
    OLLAMA_URL = "http://localhost:11434"
    EMBED_MODEL = "mxbai-embed-large"
    url = f"{OLLAMA_URL}/api/embeddings"
    payload = {"model": EMBED_MODEL, "prompt": text}

    response = requests.post(url, json=payload)
    response.raise_for_status()

    return response.json()["embedding"]
#--------------------------------------------------------------------------------------------------------
def StoreEmbeddingsInVec_db(embeddings, chunks):
    client = chromadb.PersistentClient(path="newchroma_db")
    collection = client.get_or_create_collection(name="sql_docs")
    ids = [f"chunk_{i}" for i in range(len(chunks))]
    
    collection.add(
    documents=chunks,
    embeddings=embeddings,
    ids=ids
    )
    print("Embeddings successfully stored in ChromaDB!")
    return collection
#--------------------------------------------------------------------------------------------------------
def retrieveContext(collection):
    userQuestion = "What is there"
    # Step 1: Get embedding for the question
    query_embedding = get_embedding(userQuestion)

# Step 2: Query ChromaDB
    results = collection.query(
    query_embeddings=[query_embedding],
    n_results=3  # Top 3 most similar chunks
    )

    relevant_chunks = results['documents'][0]  # It's a list of lists

# Combine them into a context
    context = "\n".join(relevant_chunks)

    return context
#--------------------------------------------------------------------------------------------------------
def makePrompt(context, userQuestion):
    promptt = f"""
    You are an SQL expert. Based on the following schema and data chunks:
    {context}

    Answer the question:
    {userQuestion}
    """
    return promptt

#--------------------------------------------------------------------------------------------------------
def ask_gemma(prompt):
    url = "http://localhost:11434/api/generate"
    payload = {"model": "gemma3:1b", "prompt": prompt}

    response = requests.post(url, json=payload)
    response.raise_for_status()

    answer = ""
    for line in response.iter_lines():
        if line:
            data = line.decode('utf-8')
            json_obj = json.loads(data)   # Or use json.loads(data) if you're sure it's clean JSON
            if 'response' in json_obj:
                answer += json_obj['response']

    return answer
#--------------------------------------------------------------------------------------------------------
def Retrieve(text):
    chunks = simple_chunk_lines(text, chunk_size=1)
    embeddings = [get_embedding(chunk) for chunk in chunks]
    coll =StoreEmbeddingsInVec_db(embeddings, chunks)
    context = retrieveContext(coll)
    return context
#--------------------------------------------------------------------------------------------------------
def QueryLLM(question, context):
    prompt = makePrompt(context, question)
    answer = ask_gemma(prompt)
    return answer
#--------------------------------------------------------------------------------------------------------

context= Retrieve(schema_text)
answer = QueryLLM("Hey, how youre doing?", context)
print(answer)
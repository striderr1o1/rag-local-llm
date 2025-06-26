import chromadb
import os
import logging
import requests
import json
import sqlite3
from addData import conn


#--------------------------------------------------------------------------------------------------------
def simple_chunk_lines(text, chunk_size=20):
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
def delete_existing_collection(name: str, db_path="newchroma_db"):
    client = chromadb.PersistentClient(path=db_path)

    try:
        collections = client.list_collections()
        for col in collections:
            if col.name == name:
                client.delete_collection(name=name)
                print(f"[+] Deleted existing collection: {name}")
                return  
        print(f"[!] Collection '{name}' not found, nothing deleted.")
    except Exception as e:
        print(f"[x] Error deleting collection '{name}': {e}")
#--------------------------------------------------------------------------------------------------------
def StoreEmbeddingsInVec_db(embeddings, chunks):
    
    delete_existing_collection("sql_docs")
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
def retrieveContext(collection, userQuestion):
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
You are an expert SQL generator. Based on the following schema and context:
{context}

Generate **only valid SQL code** with correct syntax.
- Don't mix SELECT * and DISTINCT <column>
- Avoid explanation
- Return only the SQL in a code block
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
            json_obj = json.loads(data)
            if 'response' in json_obj:
                answer += json_obj['response']
    return answer
#--------------------------------------------------------------------------------------------------------
def parsing(llm_output):
    import re

    # Remove markdown ```sql blocks
    cleaned_output = re.sub(r"```sql|```", "", llm_output, flags=re.IGNORECASE).strip()

    # Find the SQL query
    match = re.search(r"(SELECT|INSERT|UPDATE|DELETE|CREATE|DROP|WITH)[\s\S]+?;", cleaned_output, re.IGNORECASE)
    
    if match:
        return match.group(0).strip()
    else:
        print("No SQL query found in LLM output.")
        return "SQL PARSE ERROR"
    
#--------------------------------------------------------------------------------------------------------
def execute_sql(sql: str):
    conn = sqlite3.connect("ecommerce.db")
    cursor = conn.cursor()

    try:
        cursor.execute(sql)
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        result = [dict(zip(columns, row)) for row in rows]
        return result
    except Exception as e:
        return {"error": str(e)}
    finally:
        conn.close()
#--------------------------------------------------------------------------------------------------------
def Retrieve(text):
    chunks = simple_chunk_lines(text, chunk_size=1)
    embeddings = [get_embedding(chunk) for chunk in chunks]
    coll = StoreEmbeddingsInVec_db(embeddings, chunks)
    return coll

#--------------------------------------------------------------------------------------------------------
def QueryLLM(question, collection):
    context = retrieveContext(collection, question)
    prompt = makePrompt(context, question)
    llm_output = ask_gemma(prompt)
    sql = parsing(llm_output)
    query = execute_sql(sql)
    return llm_output, query


sql_query = """
SELECT id, name, email
FROM users
WHERE email LIKE '%@example.com'
LIMIT 10;
"""

result = execute_sql(sql_query)

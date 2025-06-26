import chromadb
import os
import logging
import requests
import json
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import sqlite3
from addData import conn
#from functions import simple_chunk_lines, get_embedding, delete_existing_collection, StoreEmbeddingsInVec_db, retrieveContext, makePrompt, ask_gemma, parsing, execute_sql, Retrieve, QueryLLM
import pandas as pd
import re
from fastapi.responses import JSONResponse
# Initialize FastAPI app
app = FastAPI(title="SQL RAG Assistant", version="1.0.0")

# Add CORS middleware to allow frontend connections
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic model for request body
class QueryRequest(BaseModel):
    question: str

schema_text = """
Table: users (id, name, email)
Table: orders (id, user_id, amount, date)
Table: products (id, name, price)
"""

# --------------------------------------------------------------------------------------------------------
#STEP 1: CHUNK DATA
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
#--------------------------------------------------------------------------------------------------
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
    match = re.search(r"(SELECT|INSERT|UPDATE|DELETE|CREATE|DROP|WITH)[\s\S]*?(;|$)", cleaned_output, re.IGNORECASE)
    
    if match:
        return match.group(0).strip()
    else:
        print("No SQL query found in LLM output.")
        return "SQL PARSE ERROR"

#--------------------------------------------------------------------------------------------------------
def split(text:str):
    new=text.strip("\n")
    return new

    
#--------------------------------------------------------------------------------------------------------
def execute_sql(sql: str):
    
    conn = sqlite3.connect("ecommerce.db")
    cursor = conn.cursor()
    sql = split(sql)
    print(f"[>] Executing SQL: {sql}")
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

# Initialize the collection once at startup
print("Initializing embeddings and vector database...")
collection = Retrieve(schema_text)
print("Setup complete!")


#--------------------------------------------------------------------------------------------------------
# FastAPI ENDPOINTS
#--------------------------------------------------------------------------------------------------------

@app.get("/")
async def root():
    return {"message": "SQL RAG Assistant API is running!"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "message": "API is running"}

@app.post("/query")
async def query_llm_endpoint(request: QueryRequest):
    try:
        if not request.question.strip():
            raise HTTPException(status_code=400, detail="Question cannot be empty")
        
        print(f"Received question: {request.question}")
        answer, result = QueryLLM(request.question, collection)
        print(f"Generated answer: {answer[:100]}...")
        print(f"Generated query: {result}...")
        # df= pd.DataFrame(result)
        new = []
        for i in range(len(result)):
            temp = list(result[i].items())
            result[i] = temp
        return {"answer": str(result),
                 "status": "success"}
        # return JSONResponse(content=result)
    
    except Exception as e:
        print(f"Error processing query: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing query: {str(e)}")

@app.get("/schema")
async def get_schema():
    return {"schema": schema_text}



#--------------------------------------------------------------------------------------------------------
# COMMAND LINE INTERFACE (Optional - for testing)
#--------------------------------------------------------------------------------------------------------
def run_cli():
    """Run the original command line interface"""
    userQuestion = ""
    while userQuestion != 'exit':
        print("Enter question (or 'exit' to quit): ")
        userQuestion = input()
        if userQuestion != 'exit':
            answer = QueryLLM(userQuestion, collection)
            print(f"Answer: {answer}")


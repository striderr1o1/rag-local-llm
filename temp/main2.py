import chromadb
import os
import logging
import requests
import json
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import tempfile

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

# Global variables
current_schema = """
Table: users (id, name, email)
Table: orders (id, user_id, amount, date)
Table: products (id, name, price)
"""
current_collection = None

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
def StoreEmbeddingsInVec_db(embeddings, chunks, collection_name="sql_docs"):
    client = chromadb.PersistentClient(path="newchroma_db")
    
    # Delete existing collection if it exists
    try:
        client.delete_collection(name=collection_name)
        print(f"Deleted existing collection: {collection_name}")
    except:
        pass
    
    # Create new collection
    collection = client.create_collection(name=collection_name)
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
You are an SQL expert. Based on the following schema and data chunks:
{context}
Be precise in your answer, and try to fit the answer in like max 10 lines.
Answer the question:
{userQuestion}
"""
    return promptt

#--------------------------------------------------------------------------------------------------------
def ask_gemma(prompt):
    url = "http://localhost:11434/api/generate"
    payload = {"model": "gemma3:1b", "prompt": prompt}  # Updated to use better model
    response = requests.post(url, json=payload, timeout=120)  # Added timeout
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
def Retrieve(text):
    chunks = simple_chunk_lines(text, chunk_size=1)
    embeddings = [get_embedding(chunk) for chunk in chunks]
    coll = StoreEmbeddingsInVec_db(embeddings, chunks)
    return coll

#--------------------------------------------------------------------------------------------------------
def QueryLLM(question, collection):
    context = retrieveContext(collection, question)
    prompt = makePrompt(context, question)
    answer = ask_gemma(prompt)
    return answer



# Initialize the collection once at startup
print("Initializing embeddings and vector database...")
current_collection = Retrieve(current_schema)
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
    global current_collection
    try:
        if not request.question.strip():
            raise HTTPException(status_code=400, detail="Question cannot be empty")
        
        if current_collection is None:
            raise HTTPException(status_code=500, detail="No schema loaded. Please upload a schema first.")
        
        print(f"Received question: {request.question}")
        answer = QueryLLM(request.question, current_collection)
        print(f"Generated answer: {answer[:100]}...")
        
        return {"answer": answer, "status": "success"}
    
    except Exception as e:
        print(f"Error processing query: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing query: {str(e)}")

@app.get("/schema")
async def get_schema():
    global current_schema
    return {"schema": current_schema}

@app.post("/upload-schema")
async def upload_schema(file: UploadFile = File(...)):
    global current_schema, current_collection
    try:
        # Validate file type
        if not file.filename.endswith('.txt'):
            raise HTTPException(status_code=400, detail="Only .txt files are allowed")
        
        # Read file content
        content = await file.read()
        schema_text = content.decode('utf-8')
        
        # Validate content (basic check)
        if len(schema_text.strip()) < 10:
            raise HTTPException(status_code=400, detail="Schema file appears to be empty or too short")
        
        print(f"Received schema file: {file.filename}")
        print(f"Schema content length: {len(schema_text)} characters")
        
        # Update global schema
        current_schema = schema_text
        
        # Re-initialize embeddings with new schema
        print("Re-initializing embeddings with new schema...")
        current_collection = Retrieve(schema_text)
        print("Schema updated successfully!")
        
        return {
            "message": "Schema uploaded and processed successfully",
            "filename": file.filename,
            "schema_preview": schema_text[:200] + "..." if len(schema_text) > 200 else schema_text,
            "status": "success"
        }
    
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="File must be a valid UTF-8 text file")
    except Exception as e:
        print(f"Error uploading schema: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing schema file: {str(e)}")

@app.get("/current-schema")
async def get_current_schema():
    global current_schema
    return {
        "schema": current_schema,
        "preview": current_schema[:300] + "..." if len(current_schema) > 300 else current_schema,
        "length": len(current_schema)
    }

#--------------------------------------------------------------------------------------------------------
# COMMAND LINE INTERFACE (Optional - for testing)
#--------------------------------------------------------------------------------------------------------
def run_cli():
    """Run the original command line interface"""
    global current_collection
    userQuestion = ""
    while userQuestion != 'exit':
        print("Enter question (or 'exit' to quit): ")
        userQuestion = input()
        if userQuestion != 'exit':
            answer = QueryLLM(userQuestion, current_collection)
            print(f"Answer: {answer}")

# Uncomment the line below if you want to run CLI mode
# run_cli()

#--------------------------------------------------------------------------------------------------------
# TO RUN THE SERVER:
# Save this file as main.py, then run:
# uvicorn main:app --reload --host 0.0.0.0 --port 8000
#--------------------------------------------------------------------------------------------------------
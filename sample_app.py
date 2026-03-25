import os
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pymongo import MongoClient

from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from langchain_mongodb import MongoDBAtlasVectorSearch
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser

load_dotenv()

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# --- SETUP CONNECTIONS ---
embeddings = GoogleGenerativeAIEmbeddings(model="gemini-embedding-2-preview", output_dimensionality=768)

client = MongoClient(os.getenv("MONGODB_URI"))
db_name = "website_assistant"
collection_name = "code_vectors"
collection = client[db_name][collection_name]

vector_store = MongoDBAtlasVectorSearch(
    collection=collection,
    embedding=embeddings,
    index_name="vector_index" 
)

llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.2)

# --- THE SYSTEM PROMPT ---
system_prompt = """

Add your prompt here

"""

prompt_template = ChatPromptTemplate.from_messages([
    ("system", system_prompt),
    ("human", "{question}"),
])

# --- THE RAG CHAIN ---
def format_docs(docs):
    formatted = []
    for doc in docs:
        path = doc.metadata.get("path", "unknown file")
        content = f"--- FILE: {path} ---\n{doc.page_content}"
        formatted.append(content)
    return "\n\n".join(formatted)

retriever = vector_store.as_retriever(search_kwargs={"k": 5})

rag_chain = (
    {"context": retriever | format_docs, "question": RunnablePassthrough()}
    | prompt_template
    | llm
    | StrOutputParser()
)

# --- API ROUTES ---
class ChatQuery(BaseModel):
    message: str

@app.post("/chat")
async def chat(query: ChatQuery):
    try:
        # Debugging
        print(f"--- Incoming Message: {query.message} ---")
        response = rag_chain.invoke(query.message)
        
        print(f"--- AI Response: {response} ---")
        return {"answer": response}
        
    except Exception as e:
        print(f"CRITICAL ERROR: {str(e)}") 
        return {"error": str(e)}

if __name__ == "__main__":
    import uvicorn
    # Use standard 8000 port
    uvicorn.run(app, host="0.0.0.0", port=8000)

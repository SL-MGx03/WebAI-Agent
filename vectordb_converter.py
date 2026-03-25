# setup .env Add MONGODB_URI and GOOGLE_API_KEY
# ingest_local_code(r"/yourfilepath") update your file path (Please use a different folder for your websitecode)
# before running remove unwanted code from your folder. 
# as a security step we are also removing some type of files before embedding ('.git', 'node_modules', '__pycache__', '.env', 'venv', 'private_keys')


import os
from dotenv import load_dotenv
from pymongo import MongoClient
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_community.vectorstores import MongoDBAtlasVectorSearch
from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
import time

load_dotenv()

# 1. Setup Connection
client = MongoClient(os.getenv("MONGODB_URI"))

collection = client["website_assistant"]["code_vectors"]

def ingest_local_code(directory_path):
    documents = []
    
    # List of folders/files to IGNORE (Security)
    ignored_items = {'.git', 'node_modules', '__pycache__', '.env', 'venv', 'private_keys'}

    print("Reading local files...")
    for root, dirs, files in os.walk(directory_path):
        # Filter out ignored directories
        dirs[:] = [d for d in dirs if d not in ignored_items]
        
        for file in files:
            if file.endswith((".py", ".js", ".html", ".css")) and file not in ignored_items:
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        # Wrap in a LangChain Document
                        doc = Document(
                            page_content=content, 
                            metadata={"file_name": file, "path": file_path}
                        )
                        documents.append(doc)
                except Exception as e:
                    print(f"Skipping {file} due to error: {e}")

    # 2. Split into chunks
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=150)
    chunks = text_splitter.split_documents(documents)

    # 3. Use Gemini to create vectors and upload to MongoDB
    print(f"Vectorizing {len(chunks)} chunks...")
    embeddings = GoogleGenerativeAIEmbeddings(
        model="gemini-embedding-2-preview",
        task_type="retrieval_document"
    )
    batch_size = 50
    print(f"Uploading {len(chunks)} chunks in batches of {batch_size}...")



    vector_search = MongoDBAtlasVectorSearch.from_documents(
        documents=chunks[:batch_size],
        embedding=embeddings,
        collection=collection,
        index_name="vector_index" 
    )
    for i in range(batch_size, len(chunks), batch_size):
        batch = chunks[i : i + batch_size]
        current_batch_num = (i // batch_size) + 1
        print(f"Uploading batch {current_batch_num}...")
        try:
            vector_search.add_documents(batch)
            print(f"Batch {current_batch_num} done. Waiting 40 seconds...")
            time.sleep(40) #wait to reset quota
        except Exception as e:
            if "429" in str(e):
                print("Hit rate limit again. Sleeping for 60 seconds...")
                time.sleep(60)
                vector_search.add_documents(batch) # Try again
            else:
                raise e

    print("Successfully synced all local code to MongoDB Atlas!")


ingest_local_code(r"/yourfilepath")  # add your path for your website code

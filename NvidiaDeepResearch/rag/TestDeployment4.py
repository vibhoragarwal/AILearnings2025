"""

DISABLE Z SCALER
"""

"""
Learning the Ingestion API
Now that all services are deployed, let's explore how to interact with the RAG system programmatically through its APIs. This section will demonstrate both the ingestion pipeline (adding documents to your knowledge base) and the basic query pipeline (asking questions without retrieving relevant information).

What We'll Cover:

RAG Server API: Query the system with natural language questions
Document Ingestion API: Upload and manage documents in the vector database
Document Retrieval & Reranking: See how the system finds and ranks relevant information
Two Key APIs:

RAG Query Server (Port 8081): The "front-end" for asking questions and getting answers
Ingestor Server (Port 8082): The "back-end" for processing and storing documents
Think of the RAG Server as the interface users interact with, while the Ingestor Server handles the behind-the-scenes work of building the knowledge base.







3.1 Testing the Deployment
Before we ingest documents into our knowledge base, let's test that things are working in our deployment from Section 2. We will send a query to the RAG deployment without using the knowledge base, and we expect to get back an answer.

3.1.1 Test the OpenAI-compatible /chat/completions endpoint
The RAG Query Server is your main interface for interacting with the knowledge base. It exposes an OpenAI-compatible /v1/chat/completions endpoint that makes it easy to integrate into existing applications.

Key Features:

OpenAI-compatible API: Use familiar request/response formats
Knowledge base toggle: Turn retrieval on/off with use_knowledge_base parameter
Streaming responses: Get responses token-by-token as the LLM generates them
Citation support: Optionally include source document references
Let's test the endpoint to ensure our RAG server is responding correctly:

3.1.1.1 RAG Server access.

Here we will set up the configuration for the RAG server and a helper function to print the API responses.
"""

import asyncio
import json
import time
from typing import List
import tempfile
import aiohttp

from dotenv import load_dotenv
load_dotenv("deploy/compose/.env")
async def generate_answer(payload):
    """
    Asynchronously generates an answer from the RAG server by sending a POST request with the given payload.

    This function handles both streaming and non-streaming responses from the server.
    For streaming responses (text/event-stream), it concatenates the content from multiple chunks.
    For regular JSON responses, it extracts the content directly from the response.

    Args:
        payload (dict): The request payload containing messages and other parameters for the RAG server

    Returns:
        None: Prints the generated content to stdout

    The function expects the response to be in one of two formats:
    1. Streaming response with Server-Sent Events (SSE)
    2. Regular JSON response with a choices->message->content structure
    """
    async with aiohttp.ClientSession() as session:
        url = f"{RAG_BASE_URL}/v1/chat/completions"
        async with session.post(url=url, json=payload) as response:
            # Check if we're getting a streaming response
            content_type = response.headers.get('Content-Type', '')

            if 'text/event-stream' in content_type:
                # Handle streaming response
                response_text = await response.text()
                concatenated_content = ""

                for line in response_text.split('\n'):
                    if line.startswith('data: '):
                        json_str = line[len('data: '):]
                        if json_str.strip() == '[DONE]':
                            continue
                        try:
                            json_obj = json.loads(json_str)
                            content = json_obj.get("choices", [{}])[0].get("delta", {}).get("content", "")
                            concatenated_content += content
                        except json.JSONDecodeError:
                            continue

                print(concatenated_content)
            else:
                # Handle regular JSON response
                response_json = await response.json()
                if "error" in response_json:
                    print(f"Error: {response_json['error']}")
                    return

                content = response_json.get("choices", [{}])[0].get("message", {}).get("content", "")
                print(content)


async def fetch_documents(collection_name: str = ""):
    url = f"{INGESTOR_BASE_URL}/v1/documents"
    params = {"collection_name": collection_name, "vdb_endpoint": "http://milvus:19530"}
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, params=params) as response:
                await print_raw_response(response)
        except aiohttp.ClientError as e:
            print(f"Error: {e}")

# Step 4: Delete the test document
async def delete_documents(collection_name: str = "", file_names: List[str] = []):
    url = f"{INGESTOR_BASE_URL}/v1/documents"
    params = {"collection_name": collection_name, "vdb_endpoint": "http://milvus:19530"}
    async with aiohttp.ClientSession() as session:
        try:
            async with session.delete(url, params=params, json=file_names) as response:
                await print_raw_response(response)
        except aiohttp.ClientError as e:
            print(f"Error: {e}")

async def upload_temp_doc_to_rag():
    # Step 1. Create a sample text document
    sample_text = """This is a sample text document.
    It contains multiple lines of text.
    This will be uploaded to the vector store for retrieval."""

    # Create temporary text file
    with tempfile.NamedTemporaryFile(mode='w+', suffix='.txt', delete=False) as temp_file:
        temp_file.write(sample_text)
        temp_file_path = temp_file.name

    try:
        data = {
            "vdb_endpoint": "http://milvus:19530",
            "collection_name": "multimodal_data",

            # Text chunking configuration
            "split_options": {
                "chunk_size": 1024,
                "chunk_overlap": 150
            }
        }

        # Step 2. Upload file
        form_data = aiohttp.FormData()
        form_data.add_field("documents", open(temp_file_path, "rb"),
                            filename="sample_document.txt",
                            content_type="text/plain")
        form_data.add_field("data", json.dumps(data), content_type="application/json")

        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(f"{INGESTOR_BASE_URL}/v1/documents", data=form_data) as response:
                    await print_raw_response(response)
            except aiohttp.ClientError as e:
                print(f"Error: {e}")
    finally:
        # Clean up the temporary file
        os.unlink(temp_file_path)
    print("sleeping to digest doc..")
    time.sleep(20)
    print("work up.")

async def print_raw_response(response):
    """Helper function to print API responses.
    """
    try:
        response_json = await response.json()
        print(json.dumps(response_json, indent=2))
    except aiohttp.ClientResponseError:
        print(await response.text())


"""
3.1.1.2 Test the RAG server health endpoint and chat completion endpoint

We will test both the health endpoint and chat completion functionality of our RAG server

Health Check Endpoint purpose: This endpoint performs a health check on the server. It returns a 200 status code if the server is operational.

Chat Completion Endpoint purpose: This endpoint accepts user queries and generates a response.

Note: We haven't uploaded any files into the RAG database yet. We are testing the endpoint without RAG functionality. Just to make sure things so far are running properly.

"use_knowledge_base": False,  # Disable RAG functionality
"""

# 1. Test the RAG server health endpoint to verify it's running properly
# url = f"{RAG_BASE_URL}/v1/health"
# print("\nStep 1: Testing RAG server health endpoint")
# print("-"*60)
import os

# IP address assuming all services are on the same docker network
IPADDRESS = "localhost"

# Port number for the server
ingestor_server_port = "8082"

# Base URL constructed from IP and port for making API requests
INGESTOR_BASE_URL = f"http://{IPADDRESS}:{ingestor_server_port}"

# Port number for the server
rag_server_port = "8081"

# Base URL constructed from IP and port for making API requests
RAG_BASE_URL = f"http://{IPADDRESS}:{rag_server_port}"

DATA_DIR = "data/multimodal"

async def upload_documents(collection_name: str = "") -> None:
    """
    Uploads documents from DATA_DIR to the specified collection in the vector store.

    This function:
    1. Reads all files from DATA_DIR
    2. Configures extraction and chunking options
    3. Uploads documents via POST request to the documents endpoint

    Args:
        collection_name (str): Name of the collection to upload documents to.
                             Collection must exist before uploading.

    Extraction options:
        - Extracts text, tables and charts by default
        - Uses pdfium for extraction
        - Processes at page level granularity

    Chunking options:
        - chunk_size: 1024 tokens
        - chunk_overlap: 150 tokens

    """
    # Get list of files from DATA_DIR
    files = [os.path.join(DATA_DIR, f) for f in os.listdir(DATA_DIR) if os.path.isfile(os.path.join(DATA_DIR, f))]

    # Configure upload parameters
    # Configure document processing parameters
    data = {
        # Milvus vector database endpoint
        "vdb_endpoint": "http://milvus:19530",

        # Target collection name for document storage
        "collection_name": collection_name,

        # Text chunking configuration
        "split_options": {
            "chunk_size": 1024,        # Size of each text chunk in tokens
            "chunk_overlap": 150       # Overlap between chunks in tokens
        }
    }

    # Prepare multipart form data with files and config
    form_data = aiohttp.FormData()
    for file_path in files:
        form_data.add_field("documents", open(file_path, "rb"), filename=os.path.basename(file_path), content_type="application/pdf")
    form_data.add_field("data", json.dumps(data), content_type="application/json")

    # Upload documents
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(f"{INGESTOR_BASE_URL}/v1/documents", data=form_data) as response: # Replace with session.patch for reingesting
                await print_raw_response(response)
        except aiohttp.ClientError as e:
            print(f"Error: {e}")



async def create_collections(
    collection_names: list = None,
    collection_type: str = "text",
    embedding_dimension: int = 2048
):
    """Create one or more collections in the vector store.

    Args:
        collection_names (list): List of collection names to create
        collection_type (str): Type of collection, defaults to "text"
        embedding_dimension (int): Dimension of embeddings, defaults to 2048

    Returns:
        Response from the API endpoint or error details if request fails
    """
    # Parameters for creating collections
    params = {
        "vdb_endpoint": "http://milvus:19530",  # Milvus vector DB endpoint
        "collection_type": collection_type,      # Type of collection
        "embedding_dimension": embedding_dimension # Dimension of embeddings
    }

    HEADERS = {"Content-Type": "application/json"}

    # Make API request to create collections
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(f"{INGESTOR_BASE_URL}/v1/collections",
                                  params=params,
                                  json=collection_names,
                                  headers=HEADERS) as response:
                await print_raw_response(response)
        except aiohttp.ClientError as e:
            return 500, {"error": str(e)}


# Now let's get the list of collections
async def fetch_collections():
    """Retrieve a list of all collections from the Milvus vector database.

    Makes a GET request to the ingestor API endpoint to fetch all collection names
    from the specified Milvus server.

    Returns:
        Response from the API endpoint containing the list of collections,
        or prints error message if request fails.
    """
    url = f"{INGESTOR_BASE_URL}/v1/collections"
    params = {"vdb_endpoint": "http://milvus:19530"}
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, params=params) as response:
                await print_raw_response(response)
        except aiohttp.ClientError as e:
            print(f"Error: {e}")


async def delete_collections(collection_names: List[str] = "") -> None:
    """Delete specified collections from the Milvus vector database.

    Makes a DELETE request to the ingestor API endpoint to remove the specified
    collections from the Milvus server.

    Args:
        collection_names (List[str]): List of collection names to delete.
            Defaults to empty string.

    Returns:
        None. Prints response from API or error message if request fails.

    Example:
        await delete_collections(collection_names=["collection1", "collection2"])
    """
    url = f"{INGESTOR_BASE_URL}/v1/collections"
    params = {"vdb_endpoint": "http://milvus:19530"}
    async with aiohttp.ClientSession() as session:
        try:
            async with session.delete(url, params=params, json=collection_names) as response:
                await print_raw_response(response)
        except aiohttp.ClientError as e:
            print(f"Error: {e}")

"""
Ingestion API Usage
3.2.3.1 Upload Document Endpoint

Purpose: This endpoint uploads new documents to the vector store.

You can specify the collection name where documents should be stored.

The collection must exist in the vector database before uploading documents.

Documents must not already exist in the collection. To update existing documents, use session.patch(...) instead of session.post(...)

Multiple files can be uploaded in a single request for efficiency

Configuration Options:

You can customize the document processing with these parameters:

split_options: Define how documents are chunked (size, overlap).

Smaller chunk size allows for more precise semantic matching because each chunk can focus more effectively on a specific concept, but they may lose surrounding context. Larger chunk size preserve more context and relationships between concepts, but the additional content may dilute the semantic match score and include less relevant information.

Chunk overlap defines how much overlap exists between neighboring chunks which can help preserve context and continuity in the retrieved contents.

Custom metadata: Add additional information to your documents

In this step, we'll upload the documents for ingestion.
"""
async def rag_upload_docs():
    await upload_documents(collection_name="multimodal_data")

async def upload_temp_doc_wait_delete():
    await upload_temp_doc_to_rag()
    await fetch_documents(collection_name="multimodal_data")
    await delete_documents(collection_name="multimodal_data", file_names=["sample_document.txt"])
    await fetch_documents(collection_name="multimodal_data")

async def ingestion_create_fetch_collections():

    # Test the RAG server health endpoint to verify it's running properly
    url = f"{INGESTOR_BASE_URL}/v1/health"
    print("\nStep 1: Testing ingestion server health endpoint")
    print("-" * 60)
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            await print_raw_response(response)
    # Create a collection named "multimodal_data"
    await create_collections(collection_names=["multimodal_data1"])
    await fetch_collections()
    print("\nDeleting collection 'multimodal_data1'...")
    await delete_collections(collection_names=["multimodal_data1"])
    await fetch_collections()


async def test_knowledge_base_diff(use_knowledge_base:bool):
    # IP address assuming all services are on the same docker network
    IPADDRESS = "localhost"

    # Port number for the server
    rag_server_port = "8081"

    # Base URL constructed from IP and port for making API requests
    RAG_BASE_URL = f"http://{IPADDRESS}:{rag_server_port}"  # Replace with your server URL

    url = f"{RAG_BASE_URL}/v1/chat/completions"
    payload = {
        "messages": [
            {
                "role": "user",
                "content": "Who is Nicholas Duvernay's character related to?"
            }
        ],
        "use_knowledge_base": use_knowledge_base,
        "temperature": 0.2,
        "top_p": 0.7,
        "max_tokens": 1024,
        "reranker_top_k": 10,
        "vdb_top_k": 100,
        "vdb_endpoint": "http://milvus:19530",
        "collection_name": "multimodal_data",
        "enable_query_rewriting": False,
        "enable_reranker": True,
        "enable_guardrails": False,
        "enable_citations": True,
        "model": os.environ["APP_LLM_MODELNAME"],
        "llm_endpoint": "https://integrate.api.nvidia.com/v1/chat/completions",
        "embedding_model": "nvidia/llama-3.2-nv-embedqa-1b-v2",
        "reranker_model": "nvidia/llama-3.2-nv-rerankqa-1b-v2",
        "stop": [],
    }

    await generate_answer(payload)

async def local_chat_completions_no_rag():
    # 1. Test the RAG server health endpoint


    health_url = f"{RAG_BASE_URL}/v1/health"
    print("\nStep 1: Testing RAG server health endpoint")
    print("-" * 60)

    async with aiohttp.ClientSession() as session:
        async with session.get(health_url) as response:
            await print_raw_response(response)

    # 2. Test basic chat completion endpoint
    payload = {
        "messages": [
            {
                "role": "user",
                "content": "Hi"
            }
        ],
        "use_knowledge_base": False,
        "temperature": 0.2,
        "model": os.environ["APP_LLM_MODELNAME"]
    }

    chat_url = f"{RAG_BASE_URL}/v1/chat/completions"

    print("\nStep 2: Testing chat completion endpoint")
    print("-" * 60)
    print("\nSending request to:", chat_url)
    print("\nWith payload:", json.dumps(payload, indent=2))

    async with aiohttp.ClientSession() as session:
        async with session.post(chat_url, json=payload) as response:
            await print_raw_response(response)


if __name__ == "__main__":
    # This triggers the event loop and runs the main function
    #asyncio.run(local_chat_completions_no_rag())
    #asyncio.run(ingestion_create_fetch_collections())
    #asyncio.run(rag_upload_docs())
    asyncio.run(upload_temp_doc_wait_delete())




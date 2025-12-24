"""

DISABLE Z SCALER
"""

import asyncio
import json
import os
import aiohttp

from dotenv import load_dotenv
load_dotenv("deploy/compose/.env")


# Port number for the server
rag_server_port = "8081"
# IP address assuming all services are on the same docker network
IPADDRESS = "localhost"

# Base URL constructed from IP and port for making API requests
RAG_BASE_URL = f"http://{IPADDRESS}:{rag_server_port}"

# Port number for the server
ingestor_server_port = "8082"

# Base URL constructed from IP and port for making API requests
INGESTOR_BASE_URL = f"http://{IPADDRESS}:{ingestor_server_port}"



"""
Sample Workflow: RAG-On vs. RAG-Off
Now that all services are deployed, let's see the RAG system in action! This section demonstrates the power of retrieval-augmented generation by comparing responses with and without access to the knowledge base.

Why Compare With and Without RAG?
The comparison reveals:

Hallucination Prevention: See how grounding in documents prevents the LLM from making up information
Knowledge Updates: Observe how RAG provides information beyond the LLM's training cutoff date
Source Attribution: Understand how RAG can cite specific sources for answers
Accuracy Improvement: Watch factual accuracy increase when relevant context is provided
How to Interact
You have two options for testing:

1. Through the Playground UI (Visual Interface)

Interactive chatbot interface
Easy document upload
Toggle knowledge base on/off
Real-time response streaming
See Section 2.9 for access instructions
2. Through the API (Programmatic Access)

Full control over parameters
Integration into applications
Batch processing capabilities
We'll focus on this approach below
Key API Parameters
When calling /v1/chat/completions, important parameters include:

Parameter	Purpose	Values
use_knowledge_base	Enable/disable RAG	true / false
collection_name	Which collection to search	e.g., "multimodal_data"
vdb_top_k	Number of chunks to retrieve	e.g., 100
reranker_top_k	Number of chunks after reranking	e.g., 10
enable_reranker	Use reranking for better relevance	true / false
enable_citations	Include source references	true / false
temperature	LLM creativity (0=focused, 1=creative)	0.0 - 1.0
max_tokens	Maximum response length	e.g., 1024
Testing Approach
We'll ask the same question twice:

Without RAG (use_knowledge_base: false): See what the base LLM knows
With RAG (use_knowledge_base: true): See how retrieved context improves the answer
The question will be about information in our uploaded document that the LLM wouldn't know from its training data.
"""

async def fetch_documents(collection_name: str = ""):
    url = f"{INGESTOR_BASE_URL}/v1/documents"
    params = {"collection_name": collection_name, "vdb_endpoint": "http://milvus:19530"}
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, params=params) as response:
                await print_raw_response(response)
        except aiohttp.ClientError as e:
            print(f"Error: {e}")

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
    url = f"{RAG_BASE_URL}/v1/chat/completions"
    async with aiohttp.ClientSession() as session:
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

async def print_raw_response(response):
    """Helper function to print API responses.
    """
    try:
        response_json = await response.json()
        print(json.dumps(response_json, indent=2))
    except aiohttp.ClientResponseError:
        print(await response.text())

async def upload_sample_document(collection_name: str = "") -> None:

    await health()

    sample_pdf_path =  "data/multimodal/The_White_Lotus_Season_3.pdf"

    data = {
        "vdb_endpoint": "http://milvus:19530",
        "collection_name": collection_name,
        "split_options": {
            "chunk_size": 1024,
            "chunk_overlap": 150
        }
    }

    form_data = aiohttp.FormData()
    form_data.add_field("documents",
                       open(sample_pdf_path, "rb"),
                       filename= "The_White_Lotus_Season_3.pdf",
                       content_type="application/pdf")
    form_data.add_field("data", json.dumps(data))

    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(f"{INGESTOR_BASE_URL}/v1/documents", data=form_data) as response:
                await print_raw_response(response)
        except aiohttp.ClientError as e:
            print(f"Error: {e}")
        await fetch_documents(collection_name)

async def health():
    print("\nStep 1: Testing RAG server health endpoint")
    print("-" * 60)
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{RAG_BASE_URL}/v1/health") as response:
            await print_raw_response(response)


async def test_knowledge_base_diff(use_knowledge_base:bool):

    print("use_knowledge_base", use_knowledge_base)
    # IP address assuming all services are on the same docker network
    IPADDRESS = "localhost"

    # Port number for the server
    rag_server_port = "8081"

    # Base URL constructed from IP and port for making API requests
    RAG_BASE_URL = f"http://{IPADDRESS}:{rag_server_port}"  # Replace with your server URL


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


if __name__ == "__main__":
    # This triggers the event loop and runs the main function
    #asyncio.run(local_chat_completions_no_rag())
    #asyncio.run(ingestion_create_fetch_collections())
    #asyncio.run(rag_upload_docs())
    #asyncio.run(upload_sample_document(collection_name="multimodal_data"))
    asyncio.run(test_knowledge_base_diff(use_knowledge_base=False))
    asyncio.run(test_knowledge_base_diff(use_knowledge_base=True))





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
Understanding Document Retrieval and Reranking
In the previous section, you saw RAG in action. Now let's dive deeper into how the system finds relevant information. Let's do one final workflow where we dive deep into understanding the document retrieval and reranking process that is underpinning the RAG workflow you just experienced in Section 4.

The Two-Stage Retrieval Process
RAG uses a two-stage approach to find the most relevant information:

Stage 1: Vector Similarity Search (Retrieval)
Query → Embedding → Search Milvus → Top 100 Chunks
Convert query to embedding: Your question becomes a 2048-dimensional vector
Search vector database: Find chunks with similar embeddings (semantic similarity)
Return top-k results: Retrieve the 100 most similar chunks (configurable via vdb_top_k)
Why This Works:

Embeddings capture meaning, not just keywords
"How do plants make food?" matches "photosynthesis process" semantically
Fast approximate search scales to billions of vectors
Limitation:

Initial retrieval prioritizes speed over perfect relevance
Some results may be semantically similar but contextually less relevant
Stage 2: Reranking (Relevance Refinement)
Top 100 Chunks → Reranker Model → Top 10 Best Chunks
Deep analysis: Reranker model examines each chunk more carefully
Contextual scoring: Evaluates how well each chunk answers the specific question
Reorder results: Sorts by relevance, not just semantic similarity
Select top-k: Returns the 10 most relevant chunks (configurable via reranker_top_k)
Why This Works:

Reranker uses a different model specialized for relevance
Deeper analysis considers context and question-answering fit
Smaller set of chunks means more computation per chunk is feasible
The Trade-off:

Retrieval: Fast but broad (cast a wide net)
Reranking: Slower but precise (refine the results)
Retrieval vs. Reranking Comparison
Aspect	Vector Retrieval	Reranking
Speed	Very fast (milliseconds)	Slower (needs compute per chunk)
Method	Vector similarity (cosine distance)	Cross-encoder model
Coverage	Broad (casts wide net)	Narrow (refines results)
Typical Count	100+ chunks	10-20 chunks
Focus	Semantic similarity	Question-answering relevance
Model	Embedding model	Reranking model
Why Use Both?
The two-stage approach optimizes for both recall and precision:

High Recall (Retrieval): Cast a wide net to ensure relevant chunks aren't missed
High Precision (Reranking): Refine results to surface the most relevant chunks first
Think of it like:

Retrieval = Google search (returns many results)
Reranking = Reading top results to find the best answer
Testing the Retrieval Pipeline
In the cells below, we'll:

Query without reranking: See raw vector similarity results
Query with reranking: Observe how relevance scores and order improve
Compare results: Understand the impact of each stage
This will give you insight into how the RAG pipeline finds and ranks information before passing it to the LLM for answer generation.

5.1 Utility function to print search results
First, let's create a utility function to better visualize search results:
"""

def print_search_results(response):
    """
    Nicely formats and prints search results from the RAG system.
    Also renders base64 encoded images when present.

    Args:
        response (dict): The response from the search API

    Returns:
        None: Prints formatted results to the console and displays images when applicable
    """
    if 'results' not in response or 'total_results' not in response:
        print("Invalid response format or no results found.")
        return

    print(f"\n=== SEARCH RESULTS ({response['total_results']} total) ===\n")

    for i, result in enumerate(response['results'], 1):
        print(f"Result #{i}")
        print(f"Document: {result.get('document_name', 'Unknown')}")
        print(f"Score: {result.get('score')}")

        # Handle different document types
        document_type = result.get('document_type', 'text')
        print(f"Type: {document_type}")

        print("\nContent:")
        print("-" * 80)

        content = result.get('content', '')

        # Check if content looks like base64 image data
        # Base64 images typically start with specific patterns
        is_likely_image = False
        if content and isinstance(content, str):
            # Common base64 image prefixes to check
            image_prefixes = ['iVBOR', '/9j/', 'R0lGOD', 'PD94', 'PHN2']
            is_likely_image = any(content.startswith(prefix) for prefix in image_prefixes)

        # For chart/image type documents or content that looks like base64
        if document_type in ['chart', 'image'] or is_likely_image:
            try:
                import base64
                from PIL import Image
                import io
                from IPython.display import display

                # Get base64 string and decode
                img_data = base64.b64decode(content)

                # Convert to PIL Image
                img = Image.open(io.BytesIO(img_data))

                # Display the image
                display(img)

                # Print metadata description if available
                if 'metadata' in result and 'description' in result['metadata']:
                    print(f"\nDescription: {result['metadata']['description']}")
            except Exception as e:
                print(f"Error rendering image: {str(e)}")
                print("Raw content (base64 encoded, truncated):")
                if len(content) > 100:
                    content = content[:100] + "... [base64 content truncated]"
                print(content)
        else:
            # For text documents, print the content with optional truncation
            if len(content) > 500:
                content = content[:500] + "... [content truncated]"
            print(content)

        print("-" * 80)
        print("\n")

# Search without ranking
url = f"{RAG_BASE_URL}/v1/search"
payload={
  "query": "What is the rationale for Clear Print Guidelines",
  "reranker_top_k": 3,
  "vdb_top_k": 100,
  "vdb_endpoint": "http://milvus:19530",
  "collection_name": "multimodal_data",
  "messages": [
    {
      "role": "user",
      "content": "What is the rationale for Clear Print Guidelines"
    }
  ],
  "enable_query_rewriting": False,
  "enable_reranker": False,
  "embedding_model": "nvidia/llama-3.2-nv-embedqa-1b-v2",
  "reranker_model": "nvidia/llama-3.2-nv-rerankqa-1b-v2",
}

async def document_search(payload):
    """
    Performs a search against the RAG system and prints formatted results.

    Args:
        payload (dict): The search query payload

    Returns:
        dict: The raw response from the API
    """
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(url=url, json=payload) as response:
                response_json = await response.json()
                print_search_results(response_json)  # Format and print the results
                return None  # Still return the response but it won't be printed
        except aiohttp.ClientError as e:
            print(f"Error: {e}")
            return None


if __name__ == "__main__":
    """Initial retrieval is performed using vector similarity (same as basic search)

The reranker model then examines each retrieved document more carefully
    
    It scores the relevance of each document to the specific query
    
    Results are reordered based on these relevance scores
    
    The most relevant documents appear at the top
    
    """
    payload['enable_reranker'] = False
    asyncio.run(document_search(payload))
    print("now with reranker enabled..")
    payload['enable_reranker'] = True
    asyncio.run(document_search(payload))
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
Core Components:
.
NVIDIA Nemotron Reasoning Model: You have explored this in depth in Notebook 02
NVIDIA RAG Blueprint: You have explored this in depth in Notebook 03
AIRA Backend: The agent implementation for the deep research assistant
AIRA Frontend: The frontend implementation for users to interact with the deep research assistant
Supported Features:

Deep Research: Given a report topic and desired report structure, an agent (1) creates a report plan, (2) searches data sources for answers, (3) writes a report, (4) reflects on gaps in the report for further queries, (5) finishes a report with a list of sources.
Parallel Search: During the research phase, multiple research questions are searched in parallel. For each query, the RAG service is consulted and an LLM-as-a-judge is used to check the relevancy of the results. If more information is needed, a fallback web search is performed. This search approach ensures internal documents are given preference over generic web results while maintaining accuracy. Performing query search in parallel allows for many data sources to be consulted in an efficient manner.
Human-in-the-loop: Human feedback on the report plan, interactive report edits, and Q&A with the final report.
Data Sources: Integration with the NVIDIA RAG blueprint to search multimodal documents with text, charts, and tables. Optional web search through Tavily.
Demo Web Application: Frontend web application showcasing end-to-end use of the AI-Q Research Assistant..env
"""

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

async def test(payload):
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
    asyncio.run(test(payload))
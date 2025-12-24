from dotenv import load_dotenv
import subprocess
import sys
import os
import yaml

load_dotenv("deploy/compose/.env")



print("Getting current user ID...", flush=True)
try:
    os.environ["USERID"] = subprocess.check_output("id -u", shell=True).decode().strip()
    print(f"✅ USERID set to {os.environ['USERID']}", flush=True)
except subprocess.CalledProcessError as e:
    print("❌ Failed to get USERID.", file=sys.stderr)
    print(e.stderr if hasattr(e, 'stderr') else e.output, file=sys.stderr)
    sys.exit(1)

#Set the endpoint urls of the Hosted NIMs
os.environ["APP_EMBEDDINGS_SERVERURL"] = ""
os.environ["APP_LLM_SERVERURL"] = ""
os.environ["APP_LLM_MODELNAME"] = "nvidia/llama-3.3-nemotron-super-49b-v1.5"
os.environ["APP_FILTEREXPRESSIONGENERATOR_MODELNAME"] = "nvidia/llama-3.3-nemotron-super-49b-v1.5"
os.environ["APP_FILTEREXPRESSIONGENERATOR_SERVERURL"] = ""
os.environ["SUMMARY_LLM"] = "nvidia/llama-3.3-nemotron-super-49b-v1.5"
os.environ["APP_RANKING_SERVERURL"] = ""
os.environ["SUMMARY_LLM_SERVERURL"] = ""
os.environ["OCR_HTTP_ENDPOINT"] = "https://ai.api.nvidia.com/v1/cv/baidu/paddleocr"
os.environ["OCR_INFER_PROTOCOL"] = "http"
os.environ["OCR_MODEL_NAME"] = "paddle"
os.environ["YOLOX_HTTP_ENDPOINT"] = "https://ai.api.nvidia.com/v1/cv/nvidia/nemoretriever-page-elements-v2"
os.environ["YOLOX_INFER_PROTOCOL"] = "http"
os.environ["YOLOX_GRAPHIC_ELEMENTS_HTTP_ENDPOINT"] = "https://ai.api.nvidia.com/v1/cv/nvidia/nemoretriever-graphic-elements-v1"
os.environ["YOLOX_GRAPHIC_ELEMENTS_INFER_PROTOCOL"] = "http"
os.environ["YOLOX_TABLE_STRUCTURE_HTTP_ENDPOINT"] = "https://ai.api.nvidia.com/v1/cv/nvidia/nemoretriever-table-structure-v1"
os.environ["YOLOX_TABLE_STRUCTURE_INFER_PROTOCOL"] = "http"
os.environ["APP_QUERYREWRITER_SERVERURL"] = ""
os.environ["APP_QUERYREWRITER_MODELNAME"] = "nvidia/llama-3.3-nemotron-super-49b-v1.5"
os.environ["APP_VECTORSTORE_ENABLEGPUSEARCH"] = "False"
os.environ["APP_VECTORSTORE_ENABLEGPUINDEX"] = "False"
os.environ["ENABLE_RERANKER"] = "false"



"""
Deploy the RAG Query Services
Finally, we'll deploy the RAG query services that orchestrate the retrieval and generation workflow. These services connect all the pieces together to provide the end-to-end question-answering experience.

What's Being Deployed:

RAG Server: The main orchestration service

Exposes /v1/chat/completions endpoint (OpenAI-compatible)
Exposes /v1/search endpoint for pure retrieval
Coordinates the full RAG pipeline:
Query → Embed → Search Milvus → Rerank → Add retrieved context to prompt → Call LLM → Return Answer
Supports streaming responses
Manages conversation context and history
RAG Playground (optional): Web-based UI

Interactive chatbot interface
Document upload functionality
Real-time testing and debugging
Visual feedback on retrieval and generation
API Endpoints You'll Use:

Endpoint	Purpose	Key Parameters
/v1/chat/completions	Ask questions with optional RAG	use_knowledge_base, collection_name
/v1/search	Retrieve relevant documents	query, vdb_top_k, enable_reranker
/v1/health	Check service status	None
"""
compose_file = "deploy/compose/docker-compose-rag-server.yaml"

print("Pulling RAG microservice images...", flush=True)
try:
    pull_result = subprocess.run(
        ["docker", "compose", "-f", compose_file, "pull", "--quiet"],
        env=os.environ,
        check=True,
        capture_output=True,
        text=True
    )
    print("✅ RAG images pulled successfully.", flush=True)
except subprocess.CalledProcessError as e:
    print("❌ Failed to pull RAG images.", file=sys.stderr)
    print(e.stderr, file=sys.stderr)
    sys.exit(1)

print("Starting RAG microservices...", flush=True)
try:
    up_result = subprocess.run(
        ["docker", "compose", "-f", compose_file, "up", "-d"],
        env=os.environ,
        check=True,
        capture_output=True,
        text=True
    )
    print(up_result.stdout, flush=True)
    print("✅ RAG microservices are up and running.", flush=True)
except subprocess.CalledProcessError as e:
    print("❌ Failed to start RAG microservices.", file=sys.stderr)
    print(e.stderr, file=sys.stderr)
    sys.exit(1)

print("Started RAG Microservices", flush=True)
print("-" * 60, flush=True)

# Optional: Check running containers
subprocess.run(
    ["docker", "ps", "--format", "table {{.Names}}\t{{.Status}}"],
    env=os.environ
)


"""
ingets some docs and u can select them or not and ask..
http://localhost:8090/
some errors but it works..sometime sshow same docs many ties
"""
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



print("TURN OFF ZSCALER INGESTTION SERVER FAILS....")

"""
Next, we'll deploy the services responsible for processing and ingesting documents. These services handle the complex task of extracting content from multimodal documents (PDFs with text, images, tables) and converting them into searchable embeddings.

What's Being Deployed:

NV-Ingest Runtime: NVIDIA's multimodal document processing engine

Extracts text from PDFs
Performs OCR (optical character recognition) on scanned documents and images
Detects and extracts tables, charts, and figures
Maintains document structure and layout information

Ingestor Server: API service for document management
Provides REST endpoints for uploading documents
Manages vector database collections
Coordinates the ingestion pipeline
Handles chunking of long documents and embedding generation


Redis: In-memory cache
Queues document processing jobs
Caches intermediate results
Ensures reliable job processing

The Ingestion Pipeline:
Upload PDF → NV-Ingest (extract) → Chunk Text/Tables/Images → 
Call Embedding NIM → Store in Milvus
"""

print("Pulling Ingestor Server images...needs NGC_API_KEY..", flush=True)
try:
    pull_result = subprocess.run(
        ["docker", "compose", "-f", "deploy/compose/docker-compose-ingestor-server.yaml", "pull", "--quiet"],
        env=os.environ,
        check=True,
        capture_output=True,
        text=True
    )
    print("✅ Ingestor images pulled successfully.", flush=True)
except subprocess.CalledProcessError as e:
    print("❌ Failed to pull Ingestor images.", file=sys.stderr)
    print(e.stderr, file=sys.stderr)
    sys.exit(1)

print("Starting Ingestor Server containers with build...", flush=True)
try:
    up_result = subprocess.run(
        ["docker", "compose", "-f", "deploy/compose/docker-compose-ingestor-server.yaml", "up", "-d"],
        env=os.environ,
        check=True,
        capture_output=True,
        text=True
    )
    print(up_result.stdout, flush=True)
    print("✅ Ingestor Server containers are up and running.", flush=True)
except subprocess.CalledProcessError as e:
    print("❌ Failed to start Ingestor Server containers.", file=sys.stderr)
    print(e.stderr, file=sys.stderr)
    sys.exit(1)

# Optionally check running containers
subprocess.run(
    ["docker", "ps", "--format", "table {{.Names}}\t{{.Status}}"],
    env=os.environ
)



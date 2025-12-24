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



file_path = 'deploy/compose/vectordb.yaml'

with open(file_path, 'r') as f:
    data = yaml.safe_load(f)

# We need to make some changes to the compose files to fit our environment.
# Since this self-paced course runs in a CPU-only system, let's adjust the
# Milvus vector database compose service to disable the GPU requirements.
# Navigate and remove the deploy key - disable GPU requirement on Milvus
if 'services' in data and 'milvus' in data['services']:
    if 'deploy' in data['services']['milvus']:
        del data['services']['milvus']['deploy']
        print("✓ Removed services.milvus.deploy entry")
    else:
        print("! deploy key not found under services.milvus")
else:
    print("! services.milvus not found in YAML structure")

# Write back
with open(file_path, 'w') as f:
    yaml.dump(data, f, default_flow_style=False, sort_keys=False)

print("✓ File updated successfully")


# Finally, let's reconfigure the default docker network of this blueprint to use
# the current docker network for this self-paced course.
# This allows all the services to speak to each other and us
# to access these services from this current container.

file_paths = ['deploy/compose/vectordb.yaml',
              'deploy/compose/docker-compose-ingestor-server.yaml',
              'deploy/compose/docker-compose-rag-server.yaml']

for file_path in file_paths:
    with open(file_path, 'r') as f:
        data = yaml.safe_load(f)

    if 'networks' in data and 'default' in data['networks']:
        if 'name' in data['networks']['default']:
            data['networks']['default']['name'] = "s-fx-40-v1_default"  # From nvidia-rag (default)
            print("✓ Adjusted networks.default.name entry")
        else:
            print("! name key not found under networks.default")
    else:
        print("! networks.default not found in YAML structure")

    # Write back
    with open(file_path, 'w') as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False)

print("✓ Files updated successfully")


"""
Deploy the Vector Database
Now we'll deploy Milvus, the vector database that stores and searches document embeddings. Milvus is a specialized database optimized for similarity search over high-dimensional vectors.

Why Vector Databases?
A vector database stores and indexes vector embeddings, which are numerical representations of complex, multimodal data like text, images, or audio. Vector databases are optimized for fast semantic similarity searches, allowing RAG systems to efficiently retrieve relevant information from massive amounts of unstructured data by allowing for comparison of the mathematical distances between the user query and many stored document embeddings. They're scalable and handle large datasets well because the data is pre-processed into vector embeddings once and stored in a structured format, enabling quick retrieval without repeatedly reprocessing content each time a query comes in.

What's Being Deployed
Milvus Standalone: The vector database engine

Stores embeddings (2048-dimensional vectors)
Performs fast similarity search
Supports filtering and metadata queries
MinIO: Object storage backend

Stores Milvus data files and indexes
etcd: Metadata coordination

Tracks collections, schemas, and indexes
Ensures consistency across Milvus components
Why Vector Databases?

Unlike traditional databases that search for exact matches, vector databases find semantically similar content. For example:

Query: "machine learning basics"
Would match documents about: "introduction to AI", "neural networks fundamentals", "deep learning 101"
Run the cell below to pull and start the vector database components (This can take several minutes to download and deploy):
"""

print("ENSURE..echo KEY | docker login nvcr.io -u '$oauthtoken' --password-stdin")
print("Pulling vector database images...", flush=True)
try:
    pull_result = subprocess.run(
        ["docker", "compose", "-f", "deploy/compose/vectordb.yaml", "pull", "--quiet"],
        env=os.environ,
        check=True,
        capture_output=True,
        text=True
    )
    print("✅ Images pulled successfully.", flush=True)
except subprocess.CalledProcessError as e:
    print("❌ Failed to pull images.", file=sys.stderr)
    print(e.stderr, file=sys.stderr)
    sys.exit(1)  # Exit early since next step depends on successful pull

print("Starting vector database...", flush=True)
try:
    result = subprocess.run(
        ["docker", "compose", "-f", "deploy/compose/vectordb.yaml", "up", "-d"],
        env=os.environ,
        check=True,
        capture_output=True,
        text=True
    )
    print(result.stdout, flush=True)
    print("✅ Docker Compose is up and running.", flush=True)
except subprocess.CalledProcessError as e:
    print("❌ Docker Compose failed.", file=sys.stderr)
    print(e.stderr, file=sys.stderr)
    sys.exit(1)

# Check running containers
subprocess.run(['docker', 'ps', '--format', 'table {{.Names}}\t{{.Status}}'])



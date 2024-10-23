import re
import uuid
import os
from azure.storage.blob import BlobServiceClient, BlobClient, ContainerClient
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
#from sentence_transformers import SentenceTransformer

import logging
import os
import requests
from azure.storage.blob import BlobServiceClient, BlobClient, ContainerClient
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

required_vars = [
    "AZURE_OPENAI_ENDPOINT",
    "AZURE_OPENAI_KEY",
    "AZURE_AISEARCH_ENDPOINT",
    "AZURE_AISEARCH_KEY",
    "AZURE_AISEARCH_INDEX",
    "MODEL_CHAT_DEPLOYMENT_NAME",
    "MODEL_EMBEDDINGS_DEPLOYMENT_NAME",
    "AZURE_STORAGE_ACCOUNT",
    "AZURE_STORAGE_ACCOUNT_KEY",
    "AZURE_STORAGE_CONTAINER",
    "PUBLIC_URL",
    "BLOB_NAME",
    "PAGE_NUM"
]
 
for var in required_vars:
    if not os.getenv(var):
        logger.error(f"Missing required environment variable: {var}")
        raise ValueError(f"Missing required environment variable: {var}")

# Configuration
BLOB_CONNECTION_STRING = f"DefaultEndpointsProtocol=https;AccountName={os.getenv("AZURE_STORAGE_ACCOUNT")};AccountKey={os.getenv("AZURE_STORAGE_ACCOUNT_KEY")};EndpointSuffix=core.windows.net"
BLOB_CONTAINER_NAME = f"{os.getenv("AZURE_STORAGE_CONTAINER")}"
BLOB_FILE_NAME = f"{os.getenv("BLOB_NAME")}"
PAGE_NUM = int(os.getenv("PAGE_NUM"))

SEARCH_SERVICE_ENDPOINT = os.getenv("AZURE_AISEARCH_ENDPOINT")
SEARCH_API_KEY = f"{os.getenv("AZURE_AISEARCH_KEY")}"
SEARCH_INDEX_NAME = f"{os.getenv("AZURE_AISEARCH_INDEX")}"
print(SEARCH_INDEX_NAME)

# Initialize Blob Service Client
blob_service_client = BlobServiceClient.from_connection_string(BLOB_CONNECTION_STRING)
blob_client = blob_service_client.get_blob_client(container=BLOB_CONTAINER_NAME, blob=BLOB_FILE_NAME)

# Download file from Blob Storage
download_file_path = os.path.join(os.getcwd(), BLOB_FILE_NAME)
with open(download_file_path, "wb") as download_file:
    download_file.write(blob_client.download_blob().readall())

# Process the file using Sentence Transformer
#model = SentenceTransformer('all-MiniLM-L6-v2')
with open(download_file_path, 'r', encoding="utf-8") as file:
    text = file.read()

# Document UUID
# This needs to be the same value for all sections in the same manual.
document_uuid = str(uuid.uuid4())


def generate_embeddings(text):
    headers = {
        "Content-Type": "application/json",
        "api-key": os.getenv("AZURE_OPENAI_KEY")
    }
    payload = {
        "input": text,
        "model": os.getenv("MODEL_EMBEDDINGS_DEPLOYMENT_NAME")
    }
    try:
        response = requests.post(
            f"{os.getenv('AZURE_OPENAI_ENDPOINT')}/openai/deployments/{os.getenv('MODEL_EMBEDDINGS_DEPLOYMENT_NAME')}/embeddings?api-version=2023-05-15",
            headers=headers,
            json=payload
        )
        print(response.json())
        response.raise_for_status()
        return response.json()['data'][0]['embedding']
    except requests.exceptions.RequestException as e:
        logger.error(f"Error generating embeddings: {e.response.text}")
        raise

# Split text into sections
pattern = r'\d+\.\d*\s+' # Define regex pattern to split by sections
chunks = re.split(pattern, text)
documents = []
current_position = 0

for i, chunk in enumerate(chunks):
    if chunk.strip():  # Skip empty sections
        begin = current_position
        end = current_position + len(chunk)
        embeddings = generate_embeddings(chunk)
        document = {
            "@search.action": "upload",
            "id": str(uuid.uuid4()),
            "document_num": str(document_uuid),
            "page_num": str(PAGE_NUM),
            "chunk_num": str(i),
            "chunk_begin": str(begin),
            "chunk_end": str(end),
            "chunk": str(chunk),
            "url": str(os.getenv("PUBLIC_URL")),
            "embeddings": embeddings
        }
        documents.append(document)
        current_position = end

# Initialize Search Client
search_client = SearchClient(endpoint=SEARCH_SERVICE_ENDPOINT, index_name=SEARCH_INDEX_NAME, credential=AzureKeyCredential(SEARCH_API_KEY))

# Upload documents to Azure Cognitive Search
search_client.upload_documents(documents=documents)

print("Documents uploaded successfully.")
import re
import uuid
import os
from azure.storage.blob import BlobServiceClient, BlobClient, ContainerClient
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient

import logging
import os
import requests
import time
from azure.storage.blob import BlobServiceClient, BlobClient, ContainerClient
from dotenv import load_dotenv
import fitz  # PyMuPDF

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

# Process the file
# with open(download_file_path, 'r', encoding="ISO-8859-1") as file:
#     text = file.read()

# Function to extract text from PDF
def extract_text_from_pdf(pdf_path):
    pages_text = []
    with fitz.open(pdf_path) as pdf_document:
        for page_num in range(len(pdf_document)):
            page = pdf_document.load_page(page_num)
            pages_text.append(page.get_text())
    return pages_text

# Extract text from the downloaded PDF
pages_text = extract_text_from_pdf(download_file_path)

# Function to extract text from PDF
def extract_text_from_pdf(pdf_path):
    text = ""
    with fitz.open(pdf_path) as pdf_document:
        for page_num in range(len(pdf_document)):
            page = pdf_document.load_page(page_num)
            text += page.get_text()
    return text

# Extract text from the downloaded PDF
text = extract_text_from_pdf(download_file_path)

# Document UUID
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

def count_tokens(text):
    return len(text.split())

# Function to split text into chunks based on token count
def chunk_text_by_tokens(text, max_tokens):
    words = text.split()
    chunks = []
    current_chunk = []
    current_length = 0
    for word in words:
        if current_length + len(word.split()) <= max_tokens:
            current_chunk.append(word)
            current_length += len(word.split())
        else:
            chunks.append(" ".join(current_chunk))
            current_chunk = [word]
            current_length = len(word.split())
    if current_chunk:
        chunks.append(" ".join(current_chunk))
    return chunks

pattern = r'\d+\.\d*\s+' # Define regex pattern to split by sections
sections = re.split(pattern, text)
documents = []
current_position = 0

max_tokens = 7000
chunks = []

for page_text in pages_text:
    if page_text.strip():  # Skip empty pages
        chunks.extend(chunk_text_by_tokens(page_text, max_tokens))

# for section in sections:
#     if section.strip():  # Skip empty sections
#         chunks.extend(chunk_text_by_tokens(section, max_tokens))

# def chunk_text_fixed_length(text, max_length):
#     return [text[i:i + max_length] for i in range(0, len(text), max_length)]

# chunks = chunk_text_fixed_length(text, length)

for i, chunk in enumerate(chunks):
    if chunk.strip():  # Skip empty sections
        begin = current_position
        end = current_position + len(chunk)
        embeddings = generate_embeddings(chunk)
        time.sleep(0.5)
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
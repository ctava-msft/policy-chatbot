import re
import uuid
import os
import logging
import requests
import time
from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential
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
    "MODEL_EMBEDDINGS_DEPLOYMENT_NAME"
]
 
for var in required_vars:
    if not os.getenv(var):
        logger.error(f"Missing required environment variable: {var}")
        raise ValueError(f"Missing required environment variable: {var}")

# Configuration
PDF_FILE_PATH = "content/tricare-provider-handbook.pdf"
PAGE_NUM = int(os.getenv("PAGE_NUM", "1"))  # Default to page 1 if not specified

SEARCH_SERVICE_ENDPOINT = os.getenv("AZURE_AISEARCH_ENDPOINT")
SEARCH_API_KEY = f"{os.getenv('AZURE_AISEARCH_KEY')}"
SEARCH_INDEX_NAME = f"{os.getenv('AZURE_AISEARCH_INDEX')}"
print(f"Using search index: {SEARCH_INDEX_NAME}")

# Function to extract text from PDF
def extract_text_from_pdf(pdf_path):
    pages_text = []
    try:
        with fitz.open(pdf_path) as pdf_document:
            logger.info(f"PDF has {len(pdf_document)} pages")
            for page_num in range(len(pdf_document)):
                page = pdf_document.load_page(page_num)
                pages_text.append(page.get_text())
    except Exception as e:
        logger.error(f"Error extracting text from PDF: {str(e)}")
        raise
    return pages_text

# Extract text from the local PDF
logger.info(f"Extracting text from {PDF_FILE_PATH}")
pages_text = extract_text_from_pdf(PDF_FILE_PATH)
logger.info(f"Extracted text from {len(pages_text)} pages")

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
        response.raise_for_status()
        return response.json()['data'][0]['embedding']
    except requests.exceptions.RequestException as e:
        logger.error(f"Error generating embeddings: {e.response.text}")
        raise

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

max_tokens = 7000
chunks = []

for page_text in pages_text:
    if page_text.strip():  # Skip empty pages
        chunks.extend(chunk_text_by_tokens(page_text, max_tokens))

logger.info(f"Created {len(chunks)} text chunks for embedding")

# Prepare documents for upload
documents = []
current_position = 0

for i, chunk in enumerate(chunks):
    if chunk.strip():  # Skip empty sections
        begin = current_position
        end = current_position + len(chunk)
        logger.info(f"Generating embeddings for chunk {i+1}/{len(chunks)}")
        embeddings = generate_embeddings(chunk)
        time.sleep(0.5)  # Rate limiting
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
search_client = SearchClient(endpoint=SEARCH_SERVICE_ENDPOINT, 
                            index_name=SEARCH_INDEX_NAME, 
                            credential=AzureKeyCredential(SEARCH_API_KEY))

# Upload documents to Azure Cognitive Search
logger.info(f"Uploading {len(documents)} documents to Azure AI Search")
search_client.upload_documents(documents=documents)

logger.info("Documents uploaded successfully.")
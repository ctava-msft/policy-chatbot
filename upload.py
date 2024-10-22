import logging
import os
import requests
from bs4 import BeautifulSoup
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
    "SYSTEM_MESSAGE"
]
 
for var in required_vars:
    if not os.getenv(var):
        logger.error(f"Missing required environment variable: {var}")
        raise ValueError(f"Missing required environment variable: {var}")

# Step 1: Send a GET request to the URL
url = f"{os.getenv("PUBLIC_URL")}"
response = requests.get(url, verify=False)
response.raise_for_status()  # Ensure we notice bad responses

# Step 2: Parse the HTML content using BeautifulSoup
soup = BeautifulSoup(response.content, 'html.parser')

# Step 3: Extract the desired content
# Assuming we want to extract all text within the body tag
content = soup.body.get_text(separator='\n', strip=True)

# Step 4: Connect to Azure Storage Account
# Replace with your actual connection string and container name
connection_string = f"DefaultEndpointsProtocol=https;AccountName={os.getenv("AZURE_STORAGE_ACCOUNT")};AccountKey={os.getenv("AZURE_STORAGE_ACCOUNT_KEY")};EndpointSuffix=core.windows.net"
container_name = f"{os.getenv("AZURE_STORAGE_CONTAINER")}"
blob_name = f"{os.getenv("BLOB_NAME")}"

blob_service_client = BlobServiceClient.from_connection_string(connection_string)
container_client = blob_service_client.get_container_client(container_name)

# Step 5: Upload the extracted content to a blob in the storage account
blob_client = container_client.get_blob_client(blob_name)
blob_client.upload_blob(content, overwrite=True)

print(f"Content uploaded to blob '{blob_name}' in container '{container_name}' successfully.")
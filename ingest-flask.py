import msal
import requests
import logging
import traceback
from flask import Flask, request, redirect, session, url_for, send_file, make_response
from io import BytesIO
from dotenv import load_dotenv
import os
import uuid
import re
import chardet
from azure.storage.blob import BlobServiceClient, BlobClient, ContainerClient
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient

load_dotenv()
app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Define the necessary parameters
tenant_id = "REDACTED"
client_id = "REDACTED"
authority = f"https://login.microsoftonline.com/{tenant_id}"
scope = ["https://.sharepoint.com/.default"]
site_url = "https://.sharepoint.com/sites/"


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

logging.basicConfig(level=logging.DEBUG)

# Create a public client application
msal_app = msal.PublicClientApplication(
    client_id,
    authority=authority,
)

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

BLOB_FILE_NAME = f"{os.getenv("BLOB_NAME")}"
PAGE_NUM = int(os.getenv("PAGE_NUM"))

SEARCH_SERVICE_ENDPOINT = os.getenv("AZURE_AISEARCH_ENDPOINT")
SEARCH_API_KEY = f"{os.getenv("AZURE_AISEARCH_KEY")}"
SEARCH_INDEX_NAME = f"{os.getenv("AZURE_AISEARCH_INDEX")}"
print(SEARCH_INDEX_NAME)

@app.route('/')
def index():
    auth_url = msal_app.get_authorization_request_url(scopes=scope)
    return redirect(auth_url)

@app.route('/getAToken')
def get_a_token():
    code = request.args.get('code')
    result = msal_app.acquire_token_by_authorization_code(code, scopes=scope)
    
    if "access_token" in result:
        session['token'] = result["access_token"]
        return redirect(url_for('test_authentication'))
    else:
        return f"Failed to obtain access token. Error: {result.get('error')}, Description: {result.get('error_description')}"

@app.route('/test_authentication')
def test_authentication():
    token = session.get('token')
    if not token:
        return "No token found in session."

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json;odata=verbose"
    }

    try:
        response = requests.get(f"{site_url}/_api/web/lists", headers=headers)
        response.raise_for_status()
        lists = response.json()
        return f"{lists}"
    except requests.exceptions.HTTPError as e:
        return f"Authentication failed: {e}\nResponse: {e.response.text}\n{traceback.format_exc()}"
    except Exception as e:
        return f"Authentication failed: {e}\n{traceback.format_exc()}"

@app.route('/get_document/<file_name>')
def get_document(file_name):
    token = session.get('token')
    if not token:
        return "No token found in session."

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json;odata=verbose"
    }

    try:
        # Get the file content
        response = requests.get(f"{site_url}/_api/web/GetFolderByServerRelativeUrl('/sites/AIRecipes/Shared Documents')/Files('{file_name}')/$value", headers=headers)
        response.raise_for_status()
        file_content = response.content

        # Open the PDF file
        return send_file(BytesIO(file_content), download_name=file_name, as_attachment=True)
    except requests.exceptions.HTTPError as e:
        return f"Failed to get document: {e}\nResponse: {e.response.text}\n{traceback.format_exc()}"
    except Exception as e:
        return f"Failed to get document: {e}\n{traceback.format_exc()}"

def split_text_into_chunks(text, max_tokens):
    words = text.split()
    chunks = []
    current_chunk = []

    for word in words:
        current_chunk.append(word)
        if len(current_chunk) >= max_tokens:
            chunks.append(' '.join(current_chunk))
            current_chunk = []

    if current_chunk:
        chunks.append(' '.join(current_chunk))

    return chunks

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
        #print(response.json())
        response.raise_for_status()
        return response.json()['data'][0]['embedding']
    except requests.exceptions.RequestException as e:
        logger.error(f"Error generating embeddings: {e.response.text}")
        raise

@app.route('/ingest_document/<file_name>')
def ingest_document(file_name):
    token = session.get('token')
    if not token:
        return "No token found in session."

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json;odata=verbose"
    }

    try:
        # Get the file content
        response = requests.get(f"{site_url}/_api/web/GetFolderByServerRelativeUrl('/sites/AIRecipes/Shared Documents')/Files('{file_name}')/$value", headers=headers)
        response.raise_for_status()

        file_content = response.content

        # Detect encoding
        detected_encoding = chardet.detect(file_content)['encoding']
        print(f"Detected encoding: {detected_encoding}")

        # Try decoding with detected encoding or common encodings
        try:
            if detected_encoding:
                file_text = file_content.decode(detected_encoding)
            else:
                file_text = file_content.decode('utf-8')
        except (UnicodeDecodeError, TypeError):
            try:
                file_text = file_content.decode('latin-1')
            except UnicodeDecodeError:
                try:
                    file_text = file_content.decode('windows-1252')
                except UnicodeDecodeError:
                    print("Failed to decode file content with common encodings.")
                    file_text = ""
        
        #file_content = response.content
        # Check and set encoding if necessary
        # if response.encoding is None:
        #     response.encoding = 'utf-8'  # Default to 'utf-8' if encoding is not specified
        # file_text = response.text
        # detected_encoding = chardet.detect(file_content)['encoding']
        # # Try decoding with detected encoding or common encodings
        # try:
        #     if detected_encoding:
        #         file_text = file_content.decode(detected_encoding)
        #     else:
        #         file_text = file_content.decode('utf-8')
        # except (UnicodeDecodeError, TypeError):
        #     try:
        #         file_text = file_content.decode('latin-1')
        #     except UnicodeDecodeError:
        #         try:
        #             file_text = file_content.decode('windows-1252')
        #         except UnicodeDecodeError:
        #             print("Failed to decode file content with common encodings.")
        #             file_text = ""
        document_uuid = str(uuid.uuid4())
        MAX_TOKENS = 3000
        # Split text into sections
        #pattern = r'\d+\.\d*\s+'
        #chunks = re.split(pattern, file_text)
        sentence_endings = re.compile(r'(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=\.|\?)\s')
        chunks = sentence_endings.split(file_text)
        documents = []
        current_position = 0

        for i, chunk in enumerate(chunks):
            if chunk.strip():  # Skip empty sections
                # Split chunk into smaller chunks if necessary
                smaller_chunks = split_text_into_chunks(chunk, MAX_TOKENS)
                for j, small_chunk in enumerate(smaller_chunks):
                    print(f"Chunk {i}-{j} length: {len(small_chunk.split())} tokens")
                try:
                    embeddings = generate_embeddings(small_chunk)
                    document = {
                        "@search.action": "upload",
                        "id": str(uuid.uuid4()),
                        "document_num": str(document_uuid),
                        "page_num": str(PAGE_NUM),
                        "chunk_num": f"{i}-{j}",
                        "chunk": small_chunk,
                        "embeddings": embeddings
                    }
                    documents.append(document)
                except requests.exceptions.HTTPError as e:
                    print(f"Failed to generate embeddings for chunk {i}-{j}: {e}")

        # Initialize Search Client
        search_client = SearchClient(endpoint=SEARCH_SERVICE_ENDPOINT, index_name=SEARCH_INDEX_NAME, credential=AzureKeyCredential(SEARCH_API_KEY))

        # Upload documents to Azure Cognitive Search
        search_client.upload_documents(documents=documents)

        print("Documents uploaded successfully.")
        response = make_response("Documents uploaded successfully.", 200)
        return response
    except requests.exceptions.HTTPError as e:
        return f"Failed to get document: {e}\nResponse: {e.response.text}\n{traceback.format_exc()}"
    except Exception as e:
        return f"Failed to get document: {e}\n{traceback.format_exc()}"

if __name__ == '__main__':
    app.run(debug=True)

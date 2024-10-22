import os
import logging
from datetime import datetime
from dotenv import load_dotenv
import random
import requests
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizedQuery
 
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
    "SYSTEM_MESSAGE"
]
 
for var in required_vars:
    if not os.getenv(var):
        logger.error(f"Missing required environment variable: {var}")
        raise ValueError(f"Missing required environment variable: {var}")
 
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
 
def query_azure_search(query, search_type='vector'):
    try:
        credential = AzureKeyCredential(os.getenv("AZURE_AISEARCH_KEY"))
        search_client = SearchClient(endpoint=os.getenv("AZURE_AISEARCH_ENDPOINT"),
                                     index_name=os.getenv("AZURE_AISEARCH_INDEX"),
                                     credential=credential)
        v_query = VectorizedQuery(
            vector=generate_embeddings(query),
            k_nearest_neighbors=3,
            fields="embeddings"
        )
        print(v_query)
        if search_type == 'vector':
            results = search_client.search(
                search_text=None,
                vector_queries=[v_query],
                select=["document_num", "page_num", "chunk_num", "chunk_begin", "chunk_end", "chunk", "url"],
                top=20
            )
        # elif search_type == 'hybrid':
        #     results = search_client.search(
        #         search_text=query,
        #         vector_queries=[v_query],
        #         select=["chunk_id", "parent_id", "chunk", "title"],
        #         top=20
        #     )
        else:
            raise ValueError("Invalid search type. Use 'vector' or 'hybrid'.")
       
        return list(results)
    except Exception as e:
        logger.error(f"Error querying Azure Search: {str(e)}")
        return []
 
def query_azure_openai(prompt, search_results):
    headers = {
        "Content-Type": "application/json",
        "api-key": os.getenv("AZURE_OPENAI_KEY")
    }
    content = " ".join([result['chunk'] for result in search_results])
   
    payload = {
        "messages": [
            {"role": "system", "content": f"""{os.getenv("SYSTEM_MESSAGE")}"""},
            {"role": "user", "content": f"Based on the following search results, please answer this question: {prompt}\n\nSearch Results: {content[:4000]}"}
        ],
        "max_tokens": 1000,
        "temperature": 0.3,
        "frequency_penalty": 0,
        "presence_penalty": 0,
        "top_p": 0.90,
        "stop": None
    }
    try:
        response = requests.post(
            f"{os.getenv('AZURE_OPENAI_ENDPOINT')}/openai/deployments/{os.getenv('MODEL_CHAT_DEPLOYMENT_NAME')}/chat/completions?api-version=2023-05-15",
            headers=headers,
            json=payload
        )
        response.raise_for_status()
        return response.json()['choices'][0]['message']['content']
    except requests.exceptions.RequestException as e:
        logger.error(f"Error querying Azure OpenAI: {e.response.text}")
        return None
 
def save_to_markdown(query, vector_results, hybrid_results, answer, filename="output.md"):
    try:
        random_suffix = random.randint(1000, 9999)
        filename = filename.replace(".md", f"_{random_suffix}.md")
        with open(filename, "w", encoding="utf-8") as f:
            f.write(f"# Query Result\n\n")
            f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write(f"## Query\n\n{query}\n\n")
           
            f.write("## Search Results\n\n")
            for result in vector_results:
                f.write(f"Doc Num: {result['document_num']}\n")
                f.write(f"Page Num: {result['page_num']}\n")
                f.write(f"Chunk Num: {result['chunk_num']}\n")
                f.write(f"Chunk Begin: {result['chunk_begin']}\n")
                f.write(f"Chunk End: {result['chunk_end']}\n")
                f.write(f"Chunk: {result['chunk'][:100]}...\n")
                f.write(f"URL: {result['url']}\n")
                f.write(f"Score: {result['@search.score']}\n\n")
           
            # f.write("## Hybrid Search Results\n\n")
            # for result in hybrid_results:
            #     f.write(f"Title: {result['title']}\n")
            #     f.write(f"Chunk ID: {result['chunk_id']}\n")
            #     f.write(f"Parent ID: {result['parent_id']}\n")
            #     f.write(f"Score: {result['@search.score']}\n")
            #     f.write(f"Content: {result['chunk'][:100]}...\n\n")
           
            f.write(f"## Answer\n\n{answer}\n")
        logger.info(f"Response and results saved to {filename}")
    except Exception as e:
        logger.error(f"Error saving to markdown: {str(e)}")
 
def main():
    logger.info("Starting query script execution.")
    print("Ready to accept your question.")
    query = input("Enter your question: ")
    print("", flush=True)
   
    if query:
        vector_results = query_azure_search(query, 'vector')
        #hybrid_results = query_azure_search(query, 'hybrid')
        # if vector_results:
        #     print("Vector Search Results:")
        #     for result in vector_results:
        #         print(f"Doc Num: {result['document_num']}")
        #         print(f"Page Num: {result['page_num']}")
        #         print(f"Chunk Num: {result['chunk_num']}")
        #         print(f"Chunk Begin: {result['chunk_begin']}")
        #         print(f"Chunk End: {result['chunk_end']}")
        #         print(f"Chunk: {result['chunk'][:100]}...\n")
        #         print(f"Score: {result['@search.score']}")
       
        # if vector_results:
        #     print("\nHybrid Search Results:")
        #     for result in hybrid_results:
        #         print(f"Title: {result['title']}")
        #         print(f"Chunk ID: {result['chunk_id']}")
        #         print(f"Parent ID: {result['parent_id']}")
        #         print(f"Score: {result['@search.score']}")
        #         print(f"Content: {result['chunk'][:100]}...\n")
       
        # combined_results = vector_results + hybrid_results
       
        if vector_results:
            #answer = query_azure_openai(query, combined_results)
            answer = query_azure_openai(query, vector_results)
            if answer:
                print("Answer:")
                print(answer)
                save_to_markdown(query, vector_results, vector_results, answer)
            else:
                logger.error("Failed to get a response from Azure OpenAI.")
        else:
            print("No search results found. Please check your index and query.")
    else:
        logger.warning("No query specified.")
 
if __name__ == "__main__":
    main()
import os
from openai import AzureOpenAI
from dotenv import load_dotenv

load_dotenv()

azure_openai_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "")
azure_openai_key = os.getenv("AZURE_OPENAI_KEY", "")
model_chat_deployment = os.getenv("MODEL_CHAT_DEPLOYMENT_NAME", "")
model_embeddings_deployment = os.getenv("MODEL_EMBEDDINGS_DEPLOYMENT_NAME", "")
aisearch_endpoint = os.getenv("AZURE_AISEARCH_ENDPOINT", "")
aisearch_key = os.getenv("AZURE_AISEARCH_KEY", "")
aisearch_index = os.getenv("AZURE_AISEARCH_INDEX", "")
subscription_key = os.getenv("AZURE_SUBSCRIPTION", "")

print(azure_openai_endpoint)
print(azure_openai_key)
print(model_chat_deployment)
print(model_embeddings_deployment)
print(aisearch_endpoint)
print(aisearch_key)
print(aisearch_index)
print(subscription_key)

system_prompt="You are an AI assistant that helps people find information."
user_prompt="what is my deductible and what are my nutrition benefits"

client = AzureOpenAI(
    azure_endpoint = azure_openai_endpoint,
    api_key = azure_openai_key,
    api_version = "2024-05-01-preview",
)

completion = client.chat.completions.create(
    model=model_chat_deployment,
    messages= [
        {
            "role": "system",
            "content": f"{system_prompt}."
        },
        {
            "role": "user",
            "content": f"{user_prompt}"
        }
    ],
    max_tokens=800,
    temperature=0.3,
    top_p=0.95,
    frequency_penalty=0,
    presence_penalty=0,
    stop=None,
    stream=False,
    extra_body={
      "data_sources": [{
          "type": "azure_search",
          "parameters": {
            "filter": None,
            "endpoint": f"{aisearch_endpoint}",
            "index_name": f"{aisearch_index}",
            "semantic_configuration": "azureml-default",
            "authentication": {
              "type": "api_key",
              "key": f"{aisearch_key}"
            },
            "embedding_dependency": {
              "type": "endpoint",
              "endpoint": f"{azure_openai_endpoint}/openai/deployments/{model_embeddings_deployment}/embeddings?api-version=2023-07-01-preview",
              "authentication": {
                "type": "api_key",
                "key": f"{azure_openai_key}"
              }
            },
            "query_type": "vector_simple_hybrid",
            "in_scope": True,
            "role_information": f"{system_prompt}",
            "strictness": 3,
            "top_n_documents": 3
          }
        }]
    })

print(completion.to_json())
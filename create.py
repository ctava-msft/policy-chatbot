import os
from dotenv import load_dotenv
from azure.core.credentials import AzureKeyCredential
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    SearchIndex,
    SimpleField,
    SearchFieldDataType,
    VectorSearch,
    VectorSearchAlgorithmConfiguration,
    SearchableField,
    SearchField
)

load_dotenv()

endpoint = os.getenv("AZURE_AISEARCH_ENDPOINT")
admin_key = os.getenv("AZURE_AISEARCH_ADMIN_KEY")
index_name = os.getenv("AZURE_AISEARCH_CREATE_INDEX")

credential = AzureKeyCredential(admin_key)
index_client = SearchIndexClient(endpoint=endpoint, credential=credential)

fields = [
    SimpleField(name="chunk_id", type=SearchFieldDataType.String, key=True),
    SimpleField(name="parent_id", type=SearchFieldDataType.String),
    SearchableField(name="title", type=SearchFieldDataType.String),
    SearchableField(name="chunk", type=SearchFieldDataType.String),
    SearchField(
        name="text_vector",
        type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
        vector_search_dimensions=1536,
        vector_search_configuration="vector-config",
        vector_search_profile="default"
    )
]

vector_search = VectorSearch(
    algorithm_configurations=[
        VectorSearchAlgorithmConfiguration(
            name="vector-config",
            kind="hnsw"
        )
    ]
)

index = SearchIndex(
    name=index_name,
    fields=fields,
    vector_search=vector_search
)

index_client.create_index(index)

print(f"Index '{index_name}' created successfully.")
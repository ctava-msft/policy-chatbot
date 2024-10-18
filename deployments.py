from azure.identity import DefaultAzureCredential
from azure.mgmt.cognitiveservices import CognitiveServicesManagementClient

subscription_id = '<redacted>'
resource_group = '<redacted>'
resource_name = '<redacted>'

credential = DefaultAzureCredential()
client = CognitiveServicesManagementClient(credential, subscription_id)

deployments = client.deployments.list(resource_group, resource_name)
for deployment in deployments:
    print(f"Deployment ID: {deployment.name}")
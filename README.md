---
description: This template sets up Azure AI Studio with connected resources.
page_type: sample
products:
- azure
- azure ai studio
- azure-resource-manager
urlFragment: aistudio-chat-rag
languages:
- bicep
- json
---
# Azure AI Studio Chat RAG

[![Deploy to Azure](https://raw.githubusercontent.com/Azure/azure-quickstart-templates/master/1-CONTRIBUTION-GUIDE/images/deploytoazure.svg?sanitize=true)](https://portal.azure.com/#create/Microsoft.Template/uri/https%3A%2F%2Fraw.githubusercontent.com%2Fctava-msft%2Fpolicy-chatbot%2Fmain%2Fazuredeploy.json)

This template sets up Azure AI Studio with connected resources.

Azure AI Studio is built on Azure Machine Learning as the primary resource provider and takes a dependency on the Cognitive Services (Azure AI Services) resource provider to surface model-as-a-service endpoints for Azure Speech, Azure Content Safety, and Azure OpenAI service.

An 'Azure AI Hub' is a special kind of 'Azure Machine Learning workspace', that is kind = "hub".

## Resources

The following table describes the resources created in the deployment:

| Provider and type | Description |
| - | - |
| `Microsoft.Compute` | `An Azure VM Compute` |
| `Microsoft.CognitiveServices` | `An Azure AI Services as the model-as-a-service endpoint provider` |
| `Microsoft.MachineLearningServices` | `An Azure AI Hub` |

# Setup python environment
```
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Copy sample.env to .env and enter values for the parameters.

## Scripts

Run create.py to create AISearch semantic index.

Run query.py to query AI search and open ai

## Learn more

If you are new to Azure AI studio, see:

- [Azure AI studio](https://aka.ms/aistudio/docs)

If you are new to Azure Machine Learning, see:

- [Azure Machine Learning service](https://azure.microsoft.com/services/machine-learning-service/)
- [Azure Machine Learning documentation](https://docs.microsoft.com/azure/machine-learning/)
- [Azure Machine Learning compute instance documentation](https://docs.microsoft.com/azure/machine-learning/concept-compute-instance)
- [Azure Machine Learning template reference](https://docs.microsoft.com/azure/templates/microsoft.machinelearningservices/allversions)
- [Quickstart templates](https://azure.microsoft.com/resources/templates/)

Run the 1-click deploy. Create AI Studio project. Create AI Search service. Add connections. Perform manual ingestion with import and vectorize your data. 
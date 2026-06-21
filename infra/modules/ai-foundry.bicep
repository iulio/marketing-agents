param name string
param location string

resource foundry 'Microsoft.CognitiveServices/accounts@2023-05-01' = {
  name: name
  location: location
  kind: 'AIServices'
  sku: { name: 'S0' }
  properties: {
    customSubDomainName: name
  }
}

// Deploy a model (GPT-4.1)
resource gptModel 'Microsoft.CognitiveServices/accounts/deployments@2023-05-01' = {
  name: 'gpt-4.1'
  parent: foundry
  sku: { name: 'Standard', capacity: 1 }
  properties: {
    model: {
      format: 'OpenAI'
      name: 'gpt-4.1'
      version: '2025-04-01'
    }
  }
}

output endpoint string = foundry.properties.endpoint
output key string = foundry.listKeys().key1

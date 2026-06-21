param name string
param location string

resource acr 'Microsoft.ContainerRegistry/registries@2023-11-01-preview' = {
  name: name
  location: location
  sku: { name: 'Basic' }
  properties: { adminUserEnabled: true }
}

output loginServer string = acr.properties.loginServer
output id string = acr.id

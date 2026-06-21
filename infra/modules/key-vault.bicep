param name string
param location string
param tenantId string
param objectId string  // Managed Identity principal ID

resource keyVault 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: name
  location: location
  properties: {
    tenantId: tenantId
    sku: { name: 'standard' }
    accessPolicies: [
      {
        tenantId: tenantId
        objectId: objectId
        permissions: {
          secrets: ['get', 'list', 'set']
        }
      }
    ]
  }
}

// Secrets to be stored (passed as parameters)
resource googleAdsSecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  name: 'google-ads-token'
  parent: keyVault
  properties: {
    value: googleAdsToken
  }
}

resource metaSecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  name: 'meta-token'
  parent: keyVault
  properties: {
    value: metaToken
  }
}

output vaultUri string = keyVault.properties.vaultUri

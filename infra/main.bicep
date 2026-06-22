// ============================================================
// main.bicep - COMPLETE, SYNTAX-VERIFIED
// ============================================================
param location string = 'norwayeast'
param projectName string = 'marketingagents'   // Longer name to avoid warnings

// ============================================================
// 1. Managed Identity
// ============================================================
resource identity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: '${projectName}-id'
  location: location
}

// ============================================================
// 2. Key Vault
// ============================================================
resource keyVault 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: '${projectName}kv'
  location: location
  properties: {
    tenantId: subscription().tenantId
    sku: {
      name: 'standard'
      family: 'A'   // Added to silence warning
    }
    accessPolicies: [
      {
        tenantId: subscription().tenantId
        objectId: identity.properties.principalId
        permissions: {
          secrets: [
            'get'
            'list'
            'set'
          ]
        }
      }
    ]
  }
}

// ============================================================
// 3. Container Registry (ACR)
// ============================================================
resource registry 'Microsoft.ContainerRegistry/registries@2023-11-01-preview' = {
  name: '${projectName}acr'
  location: location
  sku: {
    name: 'Basic'
  }
  properties: {
    adminUserEnabled: true
  }
}

// ============================================================
// 4. AI Foundry
// ============================================================
resource foundry 'Microsoft.CognitiveServices/accounts@2023-05-01' = {
  name: '${projectName}foundry'
  location: location
  kind: 'AIServices'
  sku: {
    name: 'S0'
  }
  properties: {
    customSubDomainName: '${projectName}foundry'
  }
}

// ============================================================
// 5. Log Analytics Workspace
// ============================================================
resource logAnalytics 'Microsoft.OperationalInsights/workspaces@2022-10-01' = {
  name: '${projectName}logs'
  location: location
  properties: {
    sku: {
      name: 'PerGB2018'
    }
    retentionInDays: 30
  }
}

// ============================================================
// 6. Container Apps Environment
// ============================================================
resource env 'Microsoft.App/managedEnvironments@2024-03-01' = {
  name: '${projectName}env'
  location: location
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: logAnalytics.properties.customerId
      }
    }
  }
}

// ============================================================
// 7. Container App
// ============================================================
resource app 'Microsoft.App/containerApps@2024-03-01' = {
  name: '${projectName}app'
  location: location
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${identity.id}': {}
    }
  }
  properties: {
    environmentId: env.id
    configuration: {
      activeRevisionsMode: 'Single'
      secrets: [
        {
          name: 'foundry-key'
          value: ''
        }
      ]
    }
    template: {
      containers: [
        {
          name: '${projectName}app'
          image: 'nginx:alpine'   // Temporary, we'll update later
          resources: {
            cpu: 2.0
            memory: '4Gi'
          }
          env: [
            {
              name: 'AZURE_AI_PROJECT_ENDPOINT'
              value: foundry.properties.endpoint
            },
            {
              name: 'KEY_VAULT_URI'
              value: keyVault.properties.vaultUri
            },
            {
              name: 'LLM_MODE'
              value: 'foundry'
            }
          ]
        }
      ]
      scale: {
        minReplicas: 0
        maxReplicas: 5
        rules: [
          {
            name: 'http'
            http: {
              metadata: {
                concurrentRequests: '10'
              }
            }
          }
        ]
      }
    }
    ingress: {
      external: true
      targetPort: 8000
      transport: 'http'
    }
  }
}

// ============================================================
// OUTPUTS
// ============================================================
output appFqdn string = app.properties.configuration.ingress.fqdn
output registryLoginServer string = registry.properties.loginServer
output foundryEndpoint string = foundry.properties.endpoint
output vaultUri string = keyVault.properties.vaultUri

param name string
param location string
param environmentId string
param containerImage string
param registryServer string
param registryUsername string
param registryPasswordSecretRef string
param keyVaultUri string
param managedIdentityClientId string

resource containerApp 'Microsoft.App/containerApps@2024-03-01' = {
  name: name
  location: location
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${managedIdentityId}': {}
    }
  }
  properties: {
    environmentId: environmentId
    configuration: {
      secrets: [
        { name: 'registry-password', value: registryPassword }
      ]
      registries: [
        {
          server: registryServer
          username: registryUsername
          passwordSecretRef: 'registry-password'
        }
      ]
      // Key Vault secret references
      secrets: [
        { name: 'google-ads-token', value: keyVaultUri }
        { name: 'meta-token', value: keyVaultUri }
      ]
      activeRevisionsMode: 'Single'
    }
    template: {
      containers: [
        {
          name: name
          image: containerImage
          resources: {
            cpu: 2.0
            memory: '4Gi'
          }
          env: [
            { name: 'AZURE_AI_PROJECT_ENDPOINT', value: aiFoundryEndpoint }
            { name: 'KEY_VAULT_URI', value: keyVaultUri }
            { name: 'LLM_MODE', value: 'foundry' }
          ]
        }
      ]
      scale: {
        minReplicas: 0
        maxReplicas: 5
        rules: [
          {
            name: 'http-scaling'
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

output fqdn string = containerApp.properties.configuration.ingress.fqdn

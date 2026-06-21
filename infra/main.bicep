param location string = resourceGroup().location
param projectName string = 'marketing-agents'
param aiFoundryName string = '${projectName}-foundry'
param acrName string = '${projectName}acr'
param keyVaultName string = '${projectName}-kv'
param envName string = '${projectName}-env'
param appName string = '${projectName}-app'
param containerImageName string = '${acrName}.azurecr.io/${appName}:latest'

// Managed Identity
module identity './modules/managed-identity.bicep' = {
  name: 'identity'
  params: {
    name: projectName
    location: location
  }
}

// Key Vault
module keyVault './modules/key-vault.bicep' = {
  name: 'keyVault'
  params: {
    name: keyVaultName
    location: location
    tenantId: subscription().tenantId
    objectId: identity.outputs.principalId
  }
}

// Container Registry
module registry './modules/container-registry.bicep' = {
  name: 'registry'
  params: {
    name: acrName
    location: location
  }
}

// AI Foundry
module foundry './modules/ai-foundry.bicep' = {
  name: 'foundry'
  params: {
    name: aiFoundryName
    location: location
  }
}

// Log Analytics Workspace
resource logAnalytics 'Microsoft.OperationalInsights/workspaces@2022-10-01' = {
  name: '${projectName}-logs'
  location: location
  properties: {
    sku: { name: 'PerGB2018' }
    retentionInDays: 30
  }
}

// Container Apps Environment
module containerEnv './modules/container-apps-env.bicep' = {
  name: 'containerEnv'
  params: {
    name: envName
    location: location
    logAnalyticsWorkspaceId: logAnalytics.id
  }
}

// Container App
module containerApp './modules/container-app.bicep' = {
  name: 'containerApp'
  params: {
    name: appName
    location: location
    environmentId: containerEnv.outputs.id
    containerImage: containerImageName
    registryServer: registry.outputs.loginServer
    registryUsername: registry.outputs.loginServer
    registryPassword: registry.listCredentials().passwords[0].value
    keyVaultUri: keyVault.outputs.vaultUri
    managedIdentityId: identity.outputs.id
    aiFoundryEndpoint: foundry.outputs.endpoint
  }
}

output appUrl string = 'https://${containerApp.outputs.fqdn}'
output foundryEndpoint string = foundry.outputs.endpoint

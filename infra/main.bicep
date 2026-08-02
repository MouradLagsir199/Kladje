// Receptenapp — Azure resources for one environment (dev or prod).
// Deploy with: az deployment group create -g <rg> -f infra/main.bicep -p environmentName=dev ...
// See docs/01-architecture.md for the shape and docs/12-manual-setup.md for what feeds this.

@description('Short environment name, used in resource naming.')
@allowed(['dev', 'prod'])
param environmentName string = 'dev'

param location string = resourceGroup().location

@description('Postgres Flexible Server is offer-restricted in West Europe on this subscription; North Europe is the nearest EU region with the required SKU available.')
param postgresLocation string = 'northeurope'

@description('Existing storage account (shared with Prakkie) to add the recipe-media container to.')
param existingStorageAccountName string = 'dlskladjedevweu'

param postgresAdminLogin string = 'receptenapp_admin'

@secure()
param postgresAdminPassword string

@description('Object id of the human operator, granted Key Vault Secrets Officer so they can paste in credentials as manual-setup steps complete.')
param deployerObjectId string

@description('Real values land here once Clerk is set up (docs/12-manual-setup.md step 3) — until then, placeholders keep the app booting instead of crash-looping on missing required config.')
@secure()
param clerkSecretKey string = 'sk_test_placeholder'
@secure()
param clerkWebhookSecret string = 'whsec_placeholder'

@description('Clerk JWKS endpoint. NOT a secret — it is public and derivable from the publishable key that ships in the client bundle. Kept as a real value rather than a placeholder on purpose: a wrong URL here fails every token with an opaque 401, which is expensive to diagnose.')
param clerkJwksUrl string = 'https://welcome-starling-18.clerk.accounts.dev/.well-known/jwks.json'

var appServicePlanName = 'receptenapp-plan-${environmentName}'
var appServiceName = 'receptenapp-api-${environmentName}'
var acrName = 'acrreceptenapp${environmentName}'
var keyVaultName = 'kv-receptenapp-${environmentName}'
var postgresServerName = 'receptenapp-pg-${environmentName}-ne'
var postgresDatabaseName = 'receptenapp_${environmentName}'
var storageContainerName = 'recipe-media'

var acrPullRoleId = subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '7f951dda-4ed3-4680-a7ca-43fe172d538d')
var keyVaultSecretsUserRoleId = subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '4633458b-17de-408a-b874-0445c86b69e6')
var keyVaultSecretsOfficerRoleId = subscriptionResourceId('Microsoft.Authorization/roleDefinitions', 'b86a8fe4-44ce-4948-aee5-eccb2c155cd7')
var storageBlobDataContributorRoleId = subscriptionResourceId('Microsoft.Authorization/roleDefinitions', 'ba92f5b4-2d11-453d-a403-e96b0029c9fe')

resource acr 'Microsoft.ContainerRegistry/registries@2023-07-01' = {
  name: acrName
  location: location
  sku: { name: 'Basic' }
  properties: { adminUserEnabled: false }
}

resource keyVault 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: keyVaultName
  location: location
  properties: {
    sku: { family: 'A', name: 'standard' }
    tenantId: subscription().tenantId
    enableRbacAuthorization: true
    enableSoftDelete: true
  }
}

resource appServicePlan 'Microsoft.Web/serverfarms@2023-12-01' = {
  name: appServicePlanName
  location: location
  kind: 'linux'
  sku: { name: 'B1', tier: 'Basic' }
  properties: { reserved: true }
}

resource appService 'Microsoft.Web/sites@2023-12-01' = {
  name: appServiceName
  location: location
  kind: 'app,linux,container'
  identity: { type: 'SystemAssigned' }
  properties: {
    serverFarmId: appServicePlan.id
    httpsOnly: true
    siteConfig: {
      linuxFxVersion: 'DOCKER|${acr.properties.loginServer}/receptenapp-api:latest'
      acrUseManagedIdentityCreds: true
      alwaysOn: true
      appSettings: [
        { name: 'WEBSITES_PORT', value: '8000' }
        { name: 'WEBSITES_CONTAINER_START_TIME_LIMIT', value: '600' }
        { name: 'ENVIRONMENT', value: environmentName }
        {
          name: 'DATABASE_URL'
          value: '@Microsoft.KeyVault(VaultName=${keyVaultName};SecretName=database-url)'
        }
        {
          name: 'CLERK_SECRET_KEY'
          value: '@Microsoft.KeyVault(VaultName=${keyVaultName};SecretName=clerk-secret-key)'
        }
        {
          name: 'CLERK_JWKS_URL'
          value: '@Microsoft.KeyVault(VaultName=${keyVaultName};SecretName=clerk-jwks-url)'
        }
        {
          name: 'CLERK_WEBHOOK_SECRET'
          value: '@Microsoft.KeyVault(VaultName=${keyVaultName};SecretName=clerk-webhook-secret)'
        }
      ]
    }
  }
}

resource acrPullAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(acr.id, appService.id, 'AcrPull')
  scope: acr
  properties: {
    principalId: appService.identity.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: acrPullRoleId
  }
}

resource kvSecretsUserAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(keyVault.id, appService.id, 'KeyVaultSecretsUser')
  scope: keyVault
  properties: {
    principalId: appService.identity.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: keyVaultSecretsUserRoleId
  }
}

resource kvSecretsOfficerAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(keyVault.id, deployerObjectId, 'KeyVaultSecretsOfficer')
  scope: keyVault
  properties: {
    principalId: deployerObjectId
    principalType: 'User'
    roleDefinitionId: keyVaultSecretsOfficerRoleId
  }
}

resource postgres 'Microsoft.DBforPostgreSQL/flexibleServers@2023-06-01-preview' = {
  name: postgresServerName
  location: postgresLocation
  sku: { name: 'Standard_B1ms', tier: 'Burstable' }
  properties: {
    version: '16'
    administratorLogin: postgresAdminLogin
    administratorLoginPassword: postgresAdminPassword
    storage: { storageSizeGB: 32 }
    backup: { backupRetentionDays: 7, geoRedundantBackup: 'Disabled' }
    network: { publicNetworkAccess: 'Enabled' }
    highAvailability: { mode: 'Disabled' }
  }
}

resource postgresDatabase 'Microsoft.DBforPostgreSQL/flexibleServers/databases@2023-06-01-preview' = {
  parent: postgres
  name: postgresDatabaseName
  properties: { charset: 'UTF8', collation: 'en_US.utf8' }
}

resource postgresAllowAzureServices 'Microsoft.DBforPostgreSQL/flexibleServers/firewallRules@2023-06-01-preview' = {
  parent: postgres
  name: 'AllowAzureServices'
  properties: { startIpAddress: '0.0.0.0', endIpAddress: '0.0.0.0' }
}

resource postgresRequireSsl 'Microsoft.DBforPostgreSQL/flexibleServers/configurations@2023-06-01-preview' = {
  parent: postgres
  name: 'require_secure_transport'
  properties: { value: 'ON', source: 'user-override' }
}

resource existingStorage 'Microsoft.Storage/storageAccounts@2023-01-01' existing = {
  name: existingStorageAccountName
}

resource blobService 'Microsoft.Storage/storageAccounts/blobServices@2023-01-01' existing = {
  parent: existingStorage
  name: 'default'
}

resource recipeMediaContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-01-01' = {
  parent: blobService
  name: storageContainerName
  properties: { publicAccess: 'None' }
}

resource storageBlobAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(recipeMediaContainer.id, appService.id, 'StorageBlobDataContributor')
  scope: recipeMediaContainer
  properties: {
    principalId: appService.identity.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: storageBlobDataContributorRoleId
  }
}

resource databaseUrlSecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: keyVault
  name: 'database-url'
  properties: {
    value: 'postgresql+asyncpg://${postgresAdminLogin}:${postgresAdminPassword}@${postgres.properties.fullyQualifiedDomainName}:5432/${postgresDatabaseName}?ssl=require'
  }
  dependsOn: [
    kvSecretsOfficerAssignment
  ]
}

// Placeholder until Clerk is set up (docs/12-manual-setup.md step 3). Update with
// `az keyvault secret set` afterwards, then restart the App Service AND change the
// app setting — App Service caches the *resolved* value of a Key Vault reference,
// so updating the secret alone does not reach a running app.
resource clerkSecretKeySecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: keyVault
  name: 'clerk-secret-key'
  properties: { value: clerkSecretKey }
  dependsOn: [
    kvSecretsOfficerAssignment
  ]
}

resource clerkJwksUrlSecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: keyVault
  name: 'clerk-jwks-url'
  properties: { value: clerkJwksUrl }
  dependsOn: [
    kvSecretsOfficerAssignment
  ]
}

resource clerkWebhookSecretSecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: keyVault
  name: 'clerk-webhook-secret'
  properties: { value: clerkWebhookSecret }
  dependsOn: [
    kvSecretsOfficerAssignment
  ]
}

output appServiceName string = appService.name
output appServiceDefaultHostname string = appService.properties.defaultHostName
output acrName string = acr.name
output acrLoginServer string = acr.properties.loginServer
output keyVaultName string = keyVault.name
output keyVaultUri string = keyVault.properties.vaultUri
output postgresServerFqdn string = postgres.properties.fullyQualifiedDomainName
output postgresDatabaseName string = postgresDatabaseName
output storageAccountName string = existingStorageAccountName
output storageContainerName string = storageContainerName

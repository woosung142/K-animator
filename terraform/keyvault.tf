data "azurerm_client_config" "current" {}
resource "azurerm_key_vault" "main" {
    name                = "kv-${azurerm_kubernetes_cluster.aks_cluster.name}"
    location            = azurerm_resource_group.aks_rg.location
    resource_group_name = azurerm_resource_group.aks_rg.name
    tenant_id           = data.azurerm_client_config.current.tenant_id
    sku_name            = "standard"

    enable_rbac_authorization = true
}

resource "azurerm_user_assigned_identity" "loki" {
    name                = "loki-identity"
    resource_group_name = azurerm_resource_group.aks_rg.name
    location            = azurerm_resource_group.aks_rg.location
}

resource "azurerm_key_vault_secret" "storage_account_key" {
    name                = "loki-storage-account-key"
    key_vault_id        = azurerm_key_vault.main.id
    value               = trimspace(azurerm_storage_account.Loki.primary_access_key)
}

resource "azurerm_role_assignment" "terraform_user_kv_admin" {
    scope               = azurerm_key_vault.main.id
    role_definition_name= "Key Vault Secrets Officer"
    principal_id        = data.azurerm_client_config.current.object_id 
}

resource "azurerm_role_assignment" "loki_identity_kv_reader" {
    scope               = azurerm_key_vault.main.id
    role_definition_name= "Key Vault Secrets User"
    principal_id        = azurerm_user_assigned_identity.loki.principal_id
}

resource "azurerm_federated_identity_credential" "loki" {
    name                = "loki-federated-credential"
    resource_group_name = azurerm_resource_group.aks_rg.name
    parent_id           = azurerm_user_assigned_identity.loki.id

    audience            = ["api://AzureADTokenExchange"]
    issuer              = azurerm_kubernetes_cluster.aks_cluster.oidc_issuer_url
    subject             = "system:serviceaccount:loki:loki"
}

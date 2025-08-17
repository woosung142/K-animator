data "azurerm_client_config" "current" {}
resource "azurerm_key_vault" "main" {
    name                = "kv-${azurerm_kubernetes_cluster.aks_cluster.name}"
    location            = azurerm_resource_group.aks_rg.location
    resource_group_name = azurerm_resource_group.aks_rg.name
    tenant_id           = data.azurerm_client_config.current.tenant_id
    sku_name            = "standard"

    enable_rbac_authorization = true
}

resource "azurerm_key_vault_secret" "storage_account_key" {
    name                = "loki-storage-account-key"
    key_vault_id        = azurerm_key_vault.main.id
    value               = azurerm_storage_account.Loki.primary_access_key
}

resource "azurerm_role_assignment" "terraform_user_kv_admin" {
    scope               = azurerm_key_vault.main.id
    role_definition_name= "Key Vault Secrets Officer"
    principal_id        = data.azurerm_client_config.current.object_id 
}

resource "azurerm_role_assignment" "aks_kubelet_kv_reader" {
    scope               = azurerm_key_vault.main.id
    role_definition_name= "Key Vault Secrets User"
    principal_id         = azurerm_kubernetes_cluster.aks_cluster.kubelet_identity[0].object_id
}

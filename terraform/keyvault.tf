data "azurerm_client_config" "current" {}
resource "azurerm_key_vault" "main" {
    name                = "kv-${azurerm_kubernetes_cluster.aks_cluster.name}"
    location            = azurerm_resource_group.aks_rg.location
    resource_group_name = azurerm_resource_group.aks_rg.name
    tenant_id           = data.azurerm_client_config.current.tenant_id
    sku_name            = "standard"
}

resource "azurerm_key_vault_secret" "storage_account_key" {
    name                = "loki-storage-account-key"
    key_vault_id        = azurerm_key_vault.main.id
    value               = azurerm_storage_account.Loki.primary_access_key
}

resource "azurerm_key_vault_access_policy" "terraform_user_policy" {
    key_vault_id       = azurerm_key_vault.main.id
    tenant_id          = data.azurerm_client_config.current.tenant_id
    object_id          = data.azurerm_client_config.current.object_id

    secret_permissions = [
        "Get",
        "List",
        "Set",
        "Delete",
        "Purge"
    ]
}

resource "azurerm_key_vault_access_policy" "aks_policy" {
    key_vault_id        = azurerm_key_vault.main.id
    tenant_id           = data.azurerm_client_config.current.tenant_id
    object_id           = azurerm_kubernetes_cluster.aks_cluster.kubelet_identity[0].object_id

    secret_permissions = [
        "Get",
        "List"
    ]
}
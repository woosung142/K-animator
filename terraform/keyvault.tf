data "azurerm_client_config" "current" {}
resource "azurerm_key_vault" "prod" {
    name                = "kv-prod-${azurerm_kubernetes_cluster.aks_cluster.name}"
    location            = azurerm_resource_group.aks_rg.location
    resource_group_name = azurerm_resource_group.aks_rg.name
    tenant_id           = data.azurerm_client_config.current.tenant_id
    sku_name            = "standard"

    enable_rbac_authorization = true
}
resource "azurerm_key_vault" "dev" {
    name                = "kv-dev-${azurerm_kubernetes_cluster.aks_cluster.name}"
    location            = azurerm_resource_group.aks_rg.location
    resource_group_name = azurerm_resource_group.aks_rg.name
    tenant_id           = data.azurerm_client_config.current.tenant_id
    sku_name            = "standard"

    enable_rbac_authorization = true

}
resource "azurerm_role_assignment" "terraform_user_kv_prod_admin" {
  scope                = azurerm_key_vault.prod.id
  role_definition_name = "Key Vault Secrets Officer"
  principal_id         = data.azurerm_client_config.current.object_id
}

resource "azurerm_role_assignment" "terraform_user_kv_dev_admin" {
  scope                = azurerm_key_vault.dev.id
  role_definition_name = "Key Vault Secrets Officer"
  principal_id         = data.azurerm_client_config.current.object_id
}
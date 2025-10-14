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
# ----------------------------------------------------
# Key Vault - dev
# ----------------------------------------------------
resource "azurerm_key_vault_secret" "dev_db_host" {
  name = "db-host-development"
  key_vault_id = azurerm_key_vault.dev.id
  value = module.auth_stack.db_fqdn
}
resource "azurerm_key_vault_secret" "dev_redis_host" {
  name = "redis-host-development"
  key_vault_id = azurerm_key_vault.dev.id
  value = module.auth_stack.redis_hostname
}
resource "azurerm_key_vault_secret" "dev_redis_password" {
  name = "redis-password-development"
  key_vault_id = azurerm_key_vault.dev.id
  value = module.auth_stack.redis_primary_key
}
# ----------------------------------------------------
# Key Vault - prod
# ----------------------------------------------------
resource "azurerm_key_vault_secret" "prod_db_host" {
  name = "db-host-default"
  key_vault_id = azurerm_key_vault.prod.id
  value = module.auth_stack_prod.db_fqdn
}
resource "azurerm_key_vault_secret" "prod_redis_host" {
  name = "redis-host-default"
  key_vault_id = azurerm_key_vault.prod.id
  value = module.auth_stack_prod.redis_hostname
}
resource "azurerm_key_vault_secret" "prod_redis_password" {
  name = "redis-password-default"
  key_vault_id = azurerm_key_vault.prod.id
  value = module.auth_stack_prod.redis_primary_key
}
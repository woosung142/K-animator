data "azurerm_storage_account" "loki_storage" {
    name                = azurerm_storage_account.Loki.name
    resource_group_name = azurerm_resource_group.aks_rg.name
}

resource "azurerm_role_assignment" "loki_identity_blob_contributor" {
    scope                = data.azurerm_storage_account.loki_storage.id
    role_definition_name = "Storage Blob Data Contributor"
    principal_id         = azurerm_user_assigned_identity.loki.principal_id
  
}
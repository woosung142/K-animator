resource "azurerm_storage_account" "Loki" {
    name                    = var.storage_account_name

    resource_group_name     = azurerm_resource_group.aks_rg.name
    location                = azurerm_resource_group.aks_rg.location

    account_tier            = "Standard"
    account_replication_type= "LRS"
}

resource "azurerm_storage_container" "Loki_data" {
    name                    = var.storage_container_name
    storage_account_name    = azurerm_storage_account.Loki.name
    container_access_type   = "private"
}
resource "azurerm_storage_account" "sa" {
  name = "${var.prefix}modelsa"
  resource_group_name = var.resource_group_name
  location = var.location
  account_tier = "Standard"
  account_replication_type = "LRS"
  tags = var.tags
}
resource "azurerm_storage_share" "share" {
  name = "${var.prefix}-sd-models"
  storage_account_name = azurerm_storage_account.sa.name
  quota = 50
}
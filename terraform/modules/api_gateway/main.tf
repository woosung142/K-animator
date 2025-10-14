resource "azurerm_api_management" "apim" {
  name                = var.apim_name
  location            = var.location
  resource_group_name = var.resource_group_name
  publisher_name = "K-Anumator Team"
  publisher_email = "garbage0233@gamil.com"
  sku_name = "Consumption_0"
}

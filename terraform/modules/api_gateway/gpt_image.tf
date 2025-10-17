resource "azurerm_api_management_api" "gpt_api" {
  name = "gpt-api"
  resource_group_name = var.resource_group_name
  api_management_name = azurerm_api_management.apim.name
  revision = "1"
  display_name = "GPT Image generate API (public)"
  path = "api/gpt"
  protocols = ["https"]
  service_url = var.gpt_url
}
# 공개 Operation에는 JWT 검증 정책 미적용
resource "azurerm_api_management_api_operation" "gpt_generate_image" {
  operation_id = "gpt-generate-image"
  api_name = azurerm_api_management_api.gpt_api.name
  api_management_name = azurerm_api_management.apim.name
  resource_group_name = var.resource_group_name
  display_name = "GPT Generate Image"
  method = "POST"
  url_template = "/generate-image"
}
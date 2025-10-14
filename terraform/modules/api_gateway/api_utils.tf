#----------------------------------------------------
# Util API 정의
#----------------------------------------------------
resource "azurerm_api_management_api" "util_api" {
  name = "util-api"
  resource_group_name = var.resource_group_name
  api_management_name = azurerm_api_management.apim.name
  revision = "1"
  display_name = "Util API"
  path = "api/utils"
  protocols = ["https"]
  service_url = var.util_url
}
# 보호된 Operation에만 JWT 검증 정책 적용 -> 포털에서
resource "azurerm_api_management_api_operation" "util_upload_image" {
  operation_id        = "upload-image"
  api_name            = azurerm_api_management_api.util_api.name
  api_management_name = azurerm_api_management.apim.name
  resource_group_name = var.resource_group_name
  display_name        = "Upload Image"
  method              = "POST"
  url_template        = "/upload-image"
}
resource "azurerm_api_management_api_operation" "util_get_speech_token" {
  operation_id        = "get-speech-token"
  api_name            = azurerm_api_management_api.util_api.name
  api_management_name = azurerm_api_management.apim.name
  resource_group_name = var.resource_group_name
  display_name        = "Get Speech Token"
  method              = "GET"
  url_template        = "/get-speech-token"
}
resource "azurerm_api_management_api_operation" "util_my_images" {
  operation_id        = "get-my-images"
  api_name            = azurerm_api_management_api.util_api.name
  api_management_name = azurerm_api_management.apim.name
  resource_group_name = var.resource_group_name
  display_name        = "Get My Images"
  method              = "GET"
  url_template        = "/my-images"
}

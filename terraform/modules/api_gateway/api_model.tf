#----------------------------------------------------
# Model API 정의
#----------------------------------------------------
resource "azurerm_api_management_api" "model_api" {
  name = "model-api"
  resource_group_name = var.resource_group_name
  api_management_name = azurerm_api_management.apim.name
  revision = "1"
  display_name = "Model Generation API"
  path = "api/model"
  protocols = ["https"]
  service_url = var.model_api_url
  subscription_required = false
}
# 보호된 Operation에만 JWT 검증 정책 적용 -> 포털에서
resource "azurerm_api_management_api_operation" "model_generate" {
  operation_id = "generate-model"
  api_name = azurerm_api_management_api.model_api.name
  api_management_name = azurerm_api_management.apim.name
  resource_group_name = var.resource_group_name
  display_name = "Generate prompt"
  method = "POST"
  url_template = "/generate-prompt"
}
resource "azurerm_api_management_api_operation" "model_generate_image" {
  operation_id = "generate-image-model"
  api_name = azurerm_api_management_api.model_api.name
  api_management_name = azurerm_api_management.apim.name
  resource_group_name = var.resource_group_name
  display_name = "Generate prompt from image"
  method = "POST"
  url_template = "/generate-image-from-prompt"
}
resource "azurerm_api_management_api_operation" "model_result" {
  operation_id = "get-result-model"
  api_name = azurerm_api_management_api.model_api.name
  api_management_name = azurerm_api_management.apim.name
  resource_group_name = var.resource_group_name
  display_name = "Get Result"
  method = "GET"
  url_template = "/result/{task_id}"

  template_parameter {
    name     = "task_id"  # url_template의 파라미터 이름과 일치
    type     = "string"   # task_id가 문자열 타입임을 명시
    required = true       # 이 파라미터는 필수 값임을 명시
  }
}
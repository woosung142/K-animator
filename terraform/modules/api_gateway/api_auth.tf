#----------------------------------------------------
# Auth API 정의 - 인증(공개)
#----------------------------------------------------
resource "azurerm_api_management_api" "auth_api" {
  name = "auth-api"
  resource_group_name = var.resource_group_name
  api_management_name = azurerm_api_management.apim.name
  revision = "1"
  display_name = "Authentication API (public)"
  path = "api/auth"
  protocols = ["https"]
  service_url = var.auth_url
  subscription_required = false
}
#Front Door 및 APIM 헬스체크용 API
resource "azurerm_api_management_api_operation" "auth_health" {
  operation_id        = "health-check"
  api_name            = azurerm_api_management_api.auth_api.name
  api_management_name = azurerm_api_management.apim.name
  resource_group_name = var.resource_group_name
  display_name        = "Health Check"
  method              = "GET"
  url_template        = "/health"
  response {
    status_code = 200
    description = "Health OK"
  }
}
# 공개 Operation에는 JWT 검증 정책 미적용
resource "azurerm_api_management_api_operation" "auth_signup" {
  operation_id = "signup-user"
  api_name = azurerm_api_management_api.auth_api.name
  api_management_name = azurerm_api_management.apim.name
  resource_group_name = var.resource_group_name
  display_name = "User Signup"
  method = "POST"
  url_template = "/signup"
}
resource "azurerm_api_management_api_operation" "auth_login" {
  operation_id = "login-user"
  api_name = azurerm_api_management_api.auth_api.name
  api_management_name = azurerm_api_management.apim.name
  resource_group_name = var.resource_group_name
  display_name = "User Login"
  method = "POST"
  url_template = "/login"
}
resource "azurerm_api_management_api_operation" "auth_refresh" {
  operation_id = "refresh-user"
  api_name = azurerm_api_management_api.auth_api.name
  api_management_name = azurerm_api_management.apim.name
  resource_group_name = var.resource_group_name
  display_name = "User Refresh"
  method = "POST"
  url_template = "/refresh"
}
#----------------------------------------------------
# Auth API 정의 - 사용자(인증필요)
#----------------------------------------------------
resource "azurerm_api_management_api" "users_api" {
  name = "users-api"
  resource_group_name = var.resource_group_name
  api_management_name = azurerm_api_management.apim.name
  revision = "1"
  display_name = "Authentication API (protected)"
  path = "api/users"
  protocols = ["https"]
  service_url = var.auth_url
  subscription_required = false
}
# 보호된 Operation에만 JWT 검증 정책 적용 -> 포털에서
resource "azurerm_api_management_api_operation" "users_logout" {
  operation_id = "logout-user"
  api_name = azurerm_api_management_api.users_api.name
  api_management_name = azurerm_api_management.apim.name
  resource_group_name = var.resource_group_name
  display_name = "User Logout"
  method = "POST"
  url_template = "/logout"
}
resource "azurerm_api_management_api_operation" "users_get_me" {
  operation_id = "get-current-user"
  api_name = azurerm_api_management_api.users_api.name
  api_management_name = azurerm_api_management.apim.name
  resource_group_name = var.resource_group_name
  display_name = "Get Current User"
  method = "GET"
  url_template = "/me"
}
resource "azurerm_api_management_api_operation" "users_delete_me" {
  operation_id = "delete-current-user"
  api_name = azurerm_api_management_api.users_api.name
  api_management_name = azurerm_api_management.apim.name
  resource_group_name = var.resource_group_name
  display_name = "Delete Current User"
  method = "DELETE"
  url_template = "/me"
}
resource "azurerm_api_management_api_operation" "users_update_me" {
  operation_id = "update-current-user"
  api_name = azurerm_api_management_api.users_api.name
  api_management_name = azurerm_api_management.apim.name
  resource_group_name = var.resource_group_name
  display_name = "Update Current Userr"
  method = "PATCH"
  url_template = "/me"
}
resource "azurerm_api_management_api_operation" "users_change_password" {
  operation_id = "change-user-password"
  api_name = azurerm_api_management_api.users_api.name
  api_management_name = azurerm_api_management.apim.name
  resource_group_name = var.resource_group_name
  display_name = "Change Password"
  method = "PATCH"
  url_template = "/me/password"
}
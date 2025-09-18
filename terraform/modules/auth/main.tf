# ----------------------------------------------------
# 'auth' 서비스를 위한 권한 부여
# ----------------------------------------------------
resource "azurerm_user_assigned_identity" "auth" {
  name                = "auth-identity-${var.k8s_namespace}"
  resource_group_name = var.resource_group_name
  location            = var.location
}

resource "azurerm_key_vault_secret" "jwt_secret" {
  name                = "jwt-secret-key"
  key_vault_id        = var.key_vault_id
  value               = "placeholder-for-jwt-secret"    # 실제 시크릿 값은 배포 후 수동으로 새 버전 추가
}

resource "azurerm_role_assignment" "auth_identity_kv_reader" {
  scope                = var.key_vault_id
  role_definition_name = "Key Vault Secrets User"
  principal_id         = azurerm_user_assigned_identity.auth.principal_id
}

resource "azurerm_federated_identity_credential" "auth" {
  name                = "auth-federated-cred-${var.k8s_namespace}"
  resource_group_name = var.resource_group_name
  parent_id           = azurerm_user_assigned_identity.auth.id
  audience            = ["api://AzureADTokenExchange"]
  issuer              = var.aks_oidc_issuer_url
  subject             = "system:serviceaccount:${var.k8s_namespace}:${var.k8s_service_account_name}"
}
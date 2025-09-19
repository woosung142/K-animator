# ===============================================================
# Loki를 위한 스토리지 계정 및 컨테이너 생성
# ===============================================================
resource "azurerm_storage_account" "Loki" {
    name                    = var.storage_account_name

    resource_group_name     = var.resource_group_name
    location                = var.location

    account_tier            = "Standard"
    account_replication_type= "LRS"
}

resource "azurerm_storage_container" "Loki_data" {
    name                    = var.storage_container_name
    storage_account_name    = var.storage_account_name
    container_access_type   = "private"
}
# ===============================================================
# Loki 스토리지 계정에 대한 수명 주기 관리
# ===============================================================
resource "azurerm_storage_management_policy" "loki_archive_policy" {
    storage_account_id = azurerm_storage_account.Loki.id

    rule {
        name    = "archive-old-loki-logs"
        enabled = true

        filters {
            blob_types = ["blockBlob"]
        }

        actions {
            base_blob {
                tier_to_archive_after_days_since_modification_greater_than = 30
                delete_after_days_since_modification_greater_than = 365
            }
        }
    }
}
# ===============================================================
# Loki 스토리지 접근을 위한 사용자 할당 ID 및 역할 할당
# ===============================================================
data "azurerm_storage_account" "loki_storage" {
    name                = var.storage_account_name
    resource_group_name = var.resource_group_name
}

resource "azurerm_user_assigned_identity" "loki" {              # Loki 전용 사용자 할당 ID
    name                = "loki-identity"
    resource_group_name = var.resource_group_name
    location            = var.location
}

resource "azurerm_role_assignment" "loki_identity_blob_contributor" {   # Loki 사용자 할당 ID에 스토리지 Blob Data Contributor 역할 할당
    scope                = data.azurerm_storage_account.loki_storage.id
    role_definition_name = "Storage Blob Data Contributor"
    principal_id         = azurerm_user_assigned_identity.loki.principal_id
  
}

resource "azurerm_federated_identity_credential" "loki" {   # AKS OIDC와 연동된 Loki 전용 사용자 할당 ID의 연합 ID 자격 증명
    name                = "loki-federated-credential"
    resource_group_name = var.resource_group_name
    parent_id           = azurerm_user_assigned_identity.loki.id

    audience            = ["api://AzureADTokenExchange"]
    issuer              = var.aks_oidc_issuer_url
    subject             = "system:serviceaccount:loki:loki"
}



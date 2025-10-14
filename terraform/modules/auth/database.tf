# ----------------------------------------------------
# DB Password 생성 및 Key Vault에 저장
# ----------------------------------------------------
resource "random_password" "db_password" {
    length           = 32
    special          = true  
}
resource "azurerm_key_vault_secret" "db_password" {
  name = "postgresql-password-${var.k8s_namespace}"
  key_vault_id = var.key_vault_id
  value = random_password.db_password.result
}
# ----------------------------------------------------
# PostgreSQL 서버 생성
# ----------------------------------------------------
resource "azurerm_postgresql_flexible_server" "auth_db" {
  name = "pgsql-${var.aks_cluster_name}-${var.k8s_namespace}"
  resource_group_name = var.resource_group_name
  location = var.location
  version = "16"    #17 버전은 고가용성이 안되서 추후 추가를 위해 16으로 설정
  delegated_subnet_id = var.subnet_id  #AKS 클러스터와 동일한 VNet / private 서브넷
  public_network_access_enabled = false #퍼블릭 액세스 비활성화

  private_dns_zone_id = var.private_dns_zone_id  #프라이빗 DNS 존 연결

  administrator_login = "psqladmin"
  administrator_password = azurerm_key_vault_secret.db_password.value

  sku_name = "B_Standard_B1ms"  #버스터 SKU -> 추후 변경 고려 (범용 SKU)
  storage_mb = 32768  #32GB
  backup_retention_days = 7

  lifecycle {
    ignore_changes = [ zone, ]  #존 변경 무시
  }
}
# ----------------------------------------------------
# 실제 데이터베이스 생성
# ----------------------------------------------------
resource "azurerm_postgresql_flexible_server_database" "auth_database" {
  name = "authdb"
  server_id = azurerm_postgresql_flexible_server.auth_db.id
  charset = "UTF8"
  collation = "en_US.utf8"
}
output "storage_account_name" {
  description = "sa 이름"
  value = azurerm_storage_account.sa.name
}
output "storage_account_key" {
  description = "저장소 엑세스 키"
  value = azurerm_storage_account.sa.primary_access_key
  sensitive = true
}
output "file_share_name" {
  description = "공유폴더 이름"
  value = azurerm_storage_share.share.name
}
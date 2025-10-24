output "storage_account_name" {
  description = "sa 이름"
  value = module.sd_storage.storage_account_name
}
output "storage_account_key" {
  description = "저장소 엑세스 키"
  value = module.sd_storage.storage_account_key
  sensitive = true
}
output "file_share_name" {
  description = "공유폴더 이름"
  value = module.sd_storage.file_share_name
}
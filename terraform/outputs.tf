 # ----------------------------------------------------
# azure files
# ----------------------------------------------------
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
# ----------------------------------------------------
# frontdoor
# ----------------------------------------------------
output "endpoint_hostname" {
  description = "Front Door 엔드포인트의 기본 호스트 이름"
  value = module.frontdoor.endpoint_hostname
}
output "endpoint_id" {
  description = "Front Door 엔드포인트의 ID"
  value = module.frontdoor.endpoint_id
}
output "profile_id" {
  description = "Front Door 프로파일 iD"
  value = module.frontdoor.profile_id
}
output "waf_policy_id" {
  description = "WAF 정책의 ID"
  value = module.frontdoor.waf_policy_id
}
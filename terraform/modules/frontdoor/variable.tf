variable "resource_group_name" {
  description = "리소스 그룹의 이름"
  type        = string
}
#----------------------------------------------------
# frontdoor Module Variables
#----------------------------------------------------
variable "prefix" {
  description = "생성될 모든 리소스 이름에 사용할 접두사"
  type        = string
}
variable "backend_host_name" {
  description = "백엔드 원본의 호스트 이름 (APIM 게이트웨이 URL)"
  type        = string
}
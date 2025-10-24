variable "storage_account_name" {
  description = "Loki가 사용할 스토리지 계정의 이름"
  type        = string
}
variable "storage_container_name" {
  description = "Loki가 사용할 스토리지 컨테이너의 이름"
  type        = string
}
variable "resource_group_name" {
  description = "리소스를 생성할 리소스 그룹의 이름"
  type        = string
}

variable "location" {
  description = "리소스를 생성할 Azure 지역"
  type        = string
}

variable "aks_oidc_issuer_url" {
  description = "AKS 클러스터의 OIDC Issuer URL"
  type        = string
}
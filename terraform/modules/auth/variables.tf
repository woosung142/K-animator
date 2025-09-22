variable "resource_group_name" {
  description = "리소스를 생성할 리소스 그룹의 이름"
  type        = string
}

variable "location" {
  description = "리소스를 생성할 Azure 지역"
  type        = string
}

variable "key_vault_id" {
  description = "JWT 시크릿을 저장할 Key Vault의 ID"
  type        = string
}

variable "aks_oidc_issuer_url" {
  description = "AKS 클러스터의 OIDC Issuer URL"
  type        = string
}
variable "k8s_namespace" {
  description = "auth 서비스가 배포될 쿠버네티스 네임스페이스"
  type        = string
}

variable "k8s_service_account_name" {
  description = "auth 파드가 사용할 쿠버네티스 서비스 어카운트 이름"
  type        = string
}
# ----------------------------------------------------
# PostgreSQL 변수
# ----------------------------------------------------
variable "subnet_id" {
  description = "PostgreSQL 서버를 배치할 위임된 서브넷의 ID"
  type        = string
}
variable "aks_cluster_name" {
  description = "AKS 클러스터 이름"
  type        = string
}
variable "private_dns_zone_id" {
  description = "PostgreSQL 서버에 연결할 프라이빗 DNS 존의 ID"
  type        = string
}
# ----------------------------------------------------
# Redis 변수
# ----------------------------------------------------
variable "redis_private_dns_zone_id" {
  description = "Azure Cache for Redis에 연결할 프라이빗 DNS 존의 ID"
  type        = string
}
variable "pe_subnet_id" {
  description = "Azure Cache for Redis를 배치할 프라이빗 엔드포인트 서브넷의 ID"
  type        = string
}
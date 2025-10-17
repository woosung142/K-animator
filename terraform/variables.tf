# ----------------------------------------------------
# Azure Kubernetes 변수
# ----------------------------------------------------
variable "location" {
  description = "Azure 지역"
  type        = string
  default     = "koreacentral"
}

variable "aks_cluster_resource_group_name" {
  description = "새로 생성할 AKS 클러스터의 리소스 그룹 이름"
  type        = string
}

variable "aks_cluster_name" {
  description = "새로 생성할 AKS 클러스터의 이름"
  type        = string
}

variable "existing_vnet_resource_group_name" {
  description = "DB VM이 속한 기존 VNet의 리소스 그룹 이름"
  type        = string
}

variable "existing_vnet_name" {
  description = "DB VM이 사용하는 기존 VNet의 이름"
  type        = string
}

variable "existing_subnet_name" {
  description = "새로운 AKS가 사용할 기존 VNet 안의 서브넷 이름"
  type        = string
}
# ----------------------------------------------------
# Azure Storage for Loki 변수
# ----------------------------------------------------
variable "storage_account_name" {
  description = "Loki 로그를 저장할 스토리지 컨테이너의 이름"
  type        = string
}

variable "storage_container_name" {
  description = "Loki 로그를 저장할 스토리지 컨테이너의 이름"
  type        = string
}
# ----------------------------------------------------
# 개발용 vm peering 변수
# ----------------------------------------------------
variable "vm_vnet_resource_group_name" {
  description = "접속하려는 VM이 있는 VNet의 리소스 그룹 이름"
  type = string
}

variable "vm_vnet_name" {
  description = "접속하려는 vm이 있는 vnet 이름"
  type = string
}
# ----------------------------------------------------
# 개발용 vm vnet 프라이빗 DNS 링크 변수
# ----------------------------------------------------
variable "private_dns_rg_name" {
  description = "프라이빗 DNS 존이 있는 리소스 그룹 이름"
  type = string
  default = "k-animator"
}
# ----------------------------------------------------
# API Gateway 변수
# ----------------------------------------------------

# --------------------------
# Backend Service Variables
# --------------------------

variable "backend_auth_url" {
  description = "The URL for the Auth backend service."
  type        = string
}

variable "backend_model_api_url" {
  description = "The URL for the Model API backend service."
  type        = string
}

variable "backend_util_url" {
  description = "The URL for the Util backend service."
  type        = string
}
variable "backend_gpt_url" {
  description = "The URL for the gpt backend service."
  type        = string
}
# --------------------------
# APIM Settings Variable
# --------------------------

variable "apim_name" {
  description = "The name of the API Management service."
  type        = string
}
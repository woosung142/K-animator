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
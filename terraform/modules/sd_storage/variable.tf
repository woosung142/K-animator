variable "location" {
  description = "리소스를 배포할 Azure 지역"
  type       = string  
}
variable "resource_group_name" {
  description = "리소스를 배포할 리소스 그룹 이름"
  type       = string
}
#----------------------------------------------------
# Storage Module Variables
#----------------------------------------------------
variable "prefix" {
  description = "리소스 이름 접두사"
}
variable "tags" {
  description = "리소스에 할당할 태그"
  type        = map(string)
  default     = {}
}
variable "location" {
  description = "리소스를 배포할 Azure 지역"
  type       = string  
}
variable "resource_group_name" {
  description = "리소스를 배포할 리소스 그룹 이름"
  type       = string
}

#----------------------------------------------------
# API Gateway Module Variables
#----------------------------------------------------
variable "apim_name" {
  description = "API Management 이름"
  type       = string
}

variable "auth_url" {
  description = "백엔드 auth의 서버 주소"
  type       = string
}

variable "model_api_url" {
  description = "백엔드 model-api의 서버 주소"
  type       = string
}

variable "util_url" {
  description = "백엔드 util의 서버 주소"
  type       = string
}

variable "gpt_url" {
  description = "백엔드 gpt의 서버 주소"
  type       = string
}
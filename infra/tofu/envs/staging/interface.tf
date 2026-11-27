variable "account_id" {
  type = string
}

variable "region" {
  type    = string
  default = "us-east-1"
}

variable "vpc_cidr" {
  type    = string
  default = "10.40.0.0/16"
}

variable "github_repository" {
  type    = string
  default = "CHARTMATE-APP/bodha-coder"
}

variable "alert_email" {
  type = string
}

variable "hq_email" {
  type = string
}

variable "mail_from_address" {
  type    = string
  default = ""
}

variable "gemini_backend" {
  type    = string
  default = "demo"

  validation {
    condition     = contains(["demo", "developer"], var.gemini_backend)
    error_message = "Staging holds synthetic notes only: use demo or developer."
  }
}

variable "image_tag" {
  type    = string
  default = "bootstrap"
}

variable "monthly_budget" {
  type    = number
  default = 100
}

variable "database_password_version" {
  type    = number
  default = 1
}

output "app_url" {
  value = module.app.app_url
}

output "deploy" {
  value = {
    AWS_REGION          = var.region
    AWS_DEPLOY_ROLE_ARN = module.deploy.role_arn
    ECS_CLUSTER         = module.app.cluster
    ECR_API_REPOSITORY  = module.app.repositories["api"]
    ECR_WEB_REPOSITORY  = module.app.repositories["web"]
    TASK_FAMILY_PREFIX  = "${local.name}-"
    TASK_SUBNETS        = join(",", module.network.public_subnet_ids)
    TASK_SECURITY_GROUP = module.network.security_groups.worker
  }
}

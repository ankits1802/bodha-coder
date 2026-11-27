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

variable "github_subject_prefix" {
  type    = string
  default = "repo:CHARTMATE-APP@294807646/bodha-coder@1474397206"
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
  default = "developer"

  validation {
    condition     = contains(["developer"], var.gemini_backend)
    error_message = "Only the developer backend is wired on AWS; vertex needs Google Cloud workload identity first."
  }
}

variable "public_url" {
  type    = string
  default = "https://bodha-coder.vercel.app"
}

variable "domain_name" {
  type    = string
  default = ""
}

variable "domain_live" {
  type    = bool
  default = false

  validation {
    condition     = !var.domain_live || var.domain_name != ""
    error_message = "domain_live needs domain_name."
  }
}

variable "google_client_id" {
  type    = string
  default = ""
}

variable "microsoft_client_id" {
  type    = string
  default = ""
}

variable "yahoo_client_id" {
  type    = string
  default = ""
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

output "backend_url" {
  value = module.app.backend_url
}

output "dns_records" {
  value = concat(module.app.site_records, module.data.mail_records)
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

terraform {
  required_version = "1.13.10"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "6.74.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "3.9.1"
    }
  }

  backend "s3" {
    key          = "production/terraform.tfstate"
    region       = "us-east-1"
    encrypt      = true
    use_lockfile = true
  }
}

provider "aws" {
  region              = var.region
  allowed_account_ids = [var.account_id]

  default_tags {
    tags = {
      Project     = "bodha-coder"
      Environment = local.environment
      ManagedBy   = "opentofu"
    }
  }
}

locals {
  environment = "production"
  stack       = "staging"
  name        = "bodha-${local.stack}"
  site_host   = var.domain_name == "" ? "" : "www.${var.domain_name}"
  admin_host  = var.domain_name == "" || var.admin_subdomain == "" ? "" : "${var.admin_subdomain}.${var.domain_name}"
  public_url  = var.domain_live ? "https://${local.site_host}" : var.public_url
  sender      = var.domain_mail_live ? "no-reply@${var.domain_name}" : var.mail_from_address
}

module "network" {
  source = "../../modules/network"
  name   = local.name
  cidr   = var.vpc_cidr
  region = var.region
}

module "data" {
  source                     = "../../modules/data"
  name                       = local.name
  secret_prefix              = "bodha/${local.stack}"
  account_id                 = var.account_id
  private_subnet_ids         = module.network.private_subnet_ids
  database_security_group_id = module.network.security_groups.database
  database_class             = "db.t4g.micro"
  database_backup_days       = 35
  database_password_version  = var.database_password_version
  hq_email                   = var.hq_email
  mail_from_address          = var.mail_from_address
  mail_domain                = var.domain_name
}

module "app" {
  source                 = "../../modules/app"
  name                   = local.name
  environment            = local.environment
  account_id             = var.account_id
  region                 = var.region
  vpc_id                 = module.network.vpc_id
  vpc_cidr               = module.network.cidr
  public_subnet_ids      = module.network.public_subnet_ids
  private_subnet_ids     = module.network.private_subnet_ids
  security_groups        = module.network.security_groups
  bucket_name            = module.data.bucket_name
  bucket_arn             = module.data.bucket_arn
  kms_key_arn            = module.data.kms_key_arn
  signing_key_arn        = module.data.signing_key_arn
  runtime_database       = var.runtime_database
  secret_arns            = module.data.secret_arns
  ses_identity_arns      = module.data.ses_identity_arns
  ses_configuration_set  = module.data.ses_configuration_set
  mail_from              = local.sender == "" ? "" : "Bodha Assure <${local.sender}>"
  gemini_backend         = var.gemini_backend
  image_tag              = var.image_tag
  desired_count          = 1
  public_url             = local.public_url
  billing                = var.billing
  sms_origination_number = var.sms_origination_number
  site_host              = local.site_host
  site_ready             = var.domain_live
  admin_host             = local.admin_host
  admin_ready            = var.admin_live
  google_client_id       = var.google_client_id
  microsoft_client_id    = var.microsoft_client_id
  yahoo_client_id        = var.yahoo_client_id
}

module "watch" {
  source              = "../../modules/watch"
  name                = local.name
  alert_email         = var.alert_email
  monthly_budget      = var.monthly_budget
  load_balancer       = module.app.load_balancer
  database_identifier = module.data.database_identifier
  region              = var.region
  cluster             = module.app.cluster
  probe_host          = var.domain_live ? local.site_host : module.app.edge_host
}

module "deploy" {
  source                = "../../modules/deploy"
  name                  = local.name
  github_subject_prefix = var.github_subject_prefix
  github_environment    = local.environment
  cluster               = module.app.cluster
  repository_arns       = module.app.repository_arns
  service_arns          = module.app.service_arns
  task_families         = module.app.task_families
  role_arns             = module.app.role_arns
  region                = var.region
  account_id            = var.account_id
}

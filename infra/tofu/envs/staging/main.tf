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
    key          = "staging/terraform.tfstate"
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
  environment = "staging"
  name        = "bodha-${local.environment}"
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
  environment                = local.environment
  account_id                 = var.account_id
  private_subnet_ids         = module.network.private_subnet_ids
  database_security_group_id = module.network.security_groups.database
  database_class             = "db.t4g.micro"
  database_backup_days       = 7
  database_password_version  = var.database_password_version
  hq_email                   = var.hq_email
  mail_from_address          = var.mail_from_address
}

module "app" {
  source                = "../../modules/app"
  name                  = local.name
  environment           = local.environment
  account_id            = var.account_id
  region                = var.region
  vpc_id                = module.network.vpc_id
  vpc_cidr              = module.network.cidr
  public_subnet_ids     = module.network.public_subnet_ids
  private_subnet_ids    = module.network.private_subnet_ids
  security_groups       = module.network.security_groups
  bucket_name           = module.data.bucket_name
  bucket_arn            = module.data.bucket_arn
  kms_key_arn           = module.data.kms_key_arn
  secret_arns           = module.data.secret_arns
  ses_identity_arn      = module.data.ses_identity_arn
  ses_configuration_set = module.data.ses_configuration_set
  mail_from             = var.mail_from_address == "" ? "" : "Bodha Coder <${var.mail_from_address}>"
  gemini_backend        = var.gemini_backend
  image_tag             = var.image_tag
  desired_count         = 1
  public_url            = var.public_url
  google_client_id      = var.google_client_id
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

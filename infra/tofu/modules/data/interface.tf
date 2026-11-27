terraform {
  required_providers {
    aws = {
      source = "hashicorp/aws"
    }
    random = {
      source = "hashicorp/random"
    }
  }
}

variable "name" {
  type = string
}

variable "environment" {
  type = string
}

variable "account_id" {
  type = string
}

variable "private_subnet_ids" {
  type = list(string)
}

variable "database_security_group_id" {
  type = string
}

variable "database_class" {
  type = string
}

variable "database_backup_days" {
  type = number
}

variable "database_password_version" {
  type = number
}

variable "hq_email" {
  type = string
}

variable "mail_from_address" {
  type = string
}

output "kms_key_arn" {
  value = aws_kms_key.this.arn
}

output "bucket_name" {
  value = aws_s3_bucket.documents.bucket
}

output "bucket_arn" {
  value = aws_s3_bucket.documents.arn
}

output "database_identifier" {
  value = aws_db_instance.this.identifier
}

output "secret_arns" {
  value = { for name, secret in aws_secretsmanager_secret.this : name => secret.arn }
}

output "ses_identity_arn" {
  value = var.mail_from_address == "" ? "" : aws_sesv2_email_identity.sender[0].arn
}

output "ses_configuration_set" {
  value = var.mail_from_address == "" ? "" : aws_sesv2_configuration_set.this[0].configuration_set_name
}

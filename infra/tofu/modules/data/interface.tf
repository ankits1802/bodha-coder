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

variable "secret_prefix" {
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

variable "mail_domain" {
  type = string
}

variable "retention_days" {
  type    = number
  default = 2557

  validation {
    condition     = var.retention_days >= 2557
    error_message = "Records are kept at least 7 years (2557 days)."
  }
}

output "kms_key_arn" {
  value = aws_kms_key.this.arn
}

output "signing_key_arn" {
  value = aws_kms_key.signing.arn
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

output "ses_identity_arns" {
  value = concat(aws_sesv2_email_identity.sender[*].arn, aws_sesv2_email_identity.domain[*].arn)
}

output "ses_configuration_set" {
  value = try(aws_sesv2_configuration_set.this[0].configuration_set_name, "")
}

output "mail_records" {
  value = var.mail_domain == "" ? [] : concat(
    [for token in aws_sesv2_email_identity.domain[0].dkim_signing_attributes[0].tokens : { name = "${token}._domainkey.${var.mail_domain}", type = "CNAME", value = "${token}.dkim.amazonses.com" }],
    [
      { name = local.mail_from_domain, type = "MX", value = "10 feedback-smtp.${data.aws_region.current.region}.amazonses.com" },
      { name = local.mail_from_domain, type = "TXT", value = "v=spf1 include:amazonses.com -all" },
    ],
  )
}

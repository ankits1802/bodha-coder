terraform {
  required_providers {
    aws = {
      source = "hashicorp/aws"
    }
    archive = {
      source = "hashicorp/archive"
    }
  }
}

variable "name" {
  type = string
}

variable "account_id" {
  type = string
}

variable "region" {
  type = string
}

variable "domain" {
  type = string
}

variable "live" {
  type = bool
}

variable "inbound_days" {
  type    = number
  default = 14

  validation {
    condition     = var.inbound_days >= 1 && var.inbound_days <= 30
    error_message = "Unread inbound mail is kept between 1 and 30 days."
  }
}

variable "kms_key_arn" {
  type = string
}

variable "source_file" {
  type = string
}

variable "retention_days" {
  type    = number
  default = 2557

  validation {
    condition     = var.retention_days >= 2557
    error_message = "Intake logs are kept at least 7 years (2557 days)."
  }
}

output "dns_records" {
  value = [{ name = var.domain, type = "MX", value = "10 inbound-smtp.${var.region}.amazonaws.com" }]
}

output "inbound_bucket_name" {
  value = aws_s3_bucket.inbound.bucket
}

output "inbound_bucket_arn" {
  value = aws_s3_bucket.inbound.arn
}

output "function_name" {
  value = aws_lambda_function.this.function_name
}

output "rule_set_name" {
  value = aws_ses_receipt_rule_set.this.rule_set_name
}

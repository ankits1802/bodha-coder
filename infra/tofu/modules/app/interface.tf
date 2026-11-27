variable "name" {
  type = string
}

variable "environment" {
  type = string
}

variable "account_id" {
  type = string
}

variable "region" {
  type = string
}

variable "vpc_id" {
  type = string
}

variable "vpc_cidr" {
  type = string
}

variable "public_subnet_ids" {
  type = list(string)
}

variable "private_subnet_ids" {
  type = list(string)
}

variable "security_groups" {
  type = map(string)
}

variable "bucket_name" {
  type = string
}

variable "bucket_arn" {
  type = string
}

variable "kms_key_arn" {
  type = string
}

variable "secret_arns" {
  type = map(string)
}

variable "ses_identity_arns" {
  type = list(string)
}

variable "ses_configuration_set" {
  type = string
}

variable "mail_from" {
  type = string
}

variable "gemini_backend" {
  type = string
}

variable "image_tag" {
  type = string
}

variable "desired_count" {
  type = number
}

variable "public_url" {
  type = string
}

variable "billing" {
  type = object({
    stripe_prices      = map(string)
    paypal_client_id   = string
    paypal_webhook_id  = string
    paypal_environment = string
    paypal_plans       = map(string)
  })
}

variable "site_host" {
  type = string
}

variable "site_ready" {
  type = bool
}

variable "google_client_id" {
  type = string
}

variable "microsoft_client_id" {
  type = string
}

variable "yahoo_client_id" {
  type = string
}

output "app_url" {
  value = local.app_url
}

output "backend_url" {
  value = "https://${aws_cloudfront_distribution.this.domain_name}"
}

output "edge_host" {
  value = aws_cloudfront_distribution.this.domain_name
}

output "site_records" {
  value = var.site_host == "" ? [] : concat(
    [for option in aws_acm_certificate.site[0].domain_validation_options : { name = trimsuffix(option.resource_record_name, "."), type = option.resource_record_type, value = trimsuffix(option.resource_record_value, ".") }],
    [{ name = var.site_host, type = "CNAME", value = aws_cloudfront_distribution.this.domain_name }],
  )
}

output "cluster" {
  value = aws_ecs_cluster.this.name
}

output "repositories" {
  value = { for key, repo in aws_ecr_repository.this : key => repo.repository_url }
}

output "repository_arns" {
  value = [for repo in aws_ecr_repository.this : repo.arn]
}

output "task_families" {
  value = { for key, task in aws_ecs_task_definition.this : key => task.family }
}

output "service_arns" {
  value = [for service in aws_ecs_service.this : service.id]
}

output "role_arns" {
  value = [aws_iam_role.execution.arn, aws_iam_role.app.arn, aws_iam_role.plain.arn]
}

output "load_balancer" {
  value = { arn_suffix = aws_lb.this.arn_suffix, api = aws_lb_target_group.api.arn_suffix, web = aws_lb_target_group.web.arn_suffix }
}

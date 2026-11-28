ephemeral "random_password" "secret_key" {
  length  = 64
  special = false
}

ephemeral "random_password" "mfa_key" {
  length           = 43
  special          = true
  override_special = "-_"
}

ephemeral "random_password" "clearinghouse_key" {
  length           = 43
  special          = true
  override_special = "-_"
}

ephemeral "random_password" "runtime" {
  length  = 40
  special = false
}

ephemeral "random_password" "hq_password" {
  length  = 24
  special = false
}

locals {
  secret_names     = ["database-url", "secret-key", "mfa-encryption-key", "clearinghouse-encryption-key", "bootstrap-hq", "google-client-secret", "microsoft-client-secret", "yahoo-client-secret", "gemini-api-key", "stripe-secret-key", "stripe-webhook-secret", "paypal-client-secret", "runtime-database-password", "runtime-database-url"]
  mail_from_domain = "mail.${var.mail_domain}"
}

resource "aws_secretsmanager_secret" "this" {
  for_each                = toset(local.secret_names)
  name                    = "${var.secret_prefix}/${each.key}"
  kms_key_id              = aws_kms_key.this.arn
  recovery_window_in_days = 7
}

locals {
  error_report_dsns = { "sentry-dsn" = var.sentry_dsn, "web-sentry-dsn" = var.web_sentry_dsn }
}

resource "aws_secretsmanager_secret" "error_reports" {
  for_each                = toset([for name, dsn in local.error_report_dsns : name if dsn != ""])
  name                    = "${var.secret_prefix}/${each.key}"
  kms_key_id              = aws_kms_key.this.arn
  recovery_window_in_days = 7
}

resource "aws_secretsmanager_secret_version" "error_reports" {
  for_each                 = aws_secretsmanager_secret.error_reports
  secret_id                = each.value.id
  secret_string_wo         = local.error_report_dsns[each.key]
  secret_string_wo_version = parseint(substr(sha256(local.error_report_dsns[each.key]), 0, 8), 16)
}

resource "aws_secretsmanager_secret_version" "database_url" {
  secret_id                = aws_secretsmanager_secret.this["database-url"].id
  secret_string_wo         = "postgresql+asyncpg://bodha_app:${ephemeral.random_password.database.result}@${aws_db_instance.this.address}:5432/bodha?ssl=require"
  secret_string_wo_version = var.database_password_version

  lifecycle {
    replace_triggered_by = [aws_db_instance.this.id]
  }
}

resource "aws_secretsmanager_secret_version" "runtime_password" {
  secret_id                = aws_secretsmanager_secret.this["runtime-database-password"].id
  secret_string_wo         = ephemeral.random_password.runtime.result
  secret_string_wo_version = var.runtime_password_version

  lifecycle {
    replace_triggered_by = [aws_db_instance.this.id]
  }
}

resource "aws_secretsmanager_secret_version" "runtime_url" {
  secret_id                = aws_secretsmanager_secret.this["runtime-database-url"].id
  secret_string_wo         = "postgresql+asyncpg://bodha_runtime:${ephemeral.random_password.runtime.result}@${aws_db_instance.this.address}:5432/bodha?ssl=require"
  secret_string_wo_version = var.runtime_password_version

  lifecycle {
    replace_triggered_by = [aws_db_instance.this.id]
  }
}

resource "aws_secretsmanager_secret_version" "secret_key" {
  secret_id                = aws_secretsmanager_secret.this["secret-key"].id
  secret_string_wo         = ephemeral.random_password.secret_key.result
  secret_string_wo_version = 1
}

resource "aws_secretsmanager_secret_version" "mfa_key" {
  secret_id                = aws_secretsmanager_secret.this["mfa-encryption-key"].id
  secret_string_wo         = "${ephemeral.random_password.mfa_key.result}="
  secret_string_wo_version = 1
}

resource "aws_secretsmanager_secret_version" "clearinghouse_key" {
  secret_id                = aws_secretsmanager_secret.this["clearinghouse-encryption-key"].id
  secret_string_wo         = "${ephemeral.random_password.clearinghouse_key.result}="
  secret_string_wo_version = 1
}

resource "aws_secretsmanager_secret_version" "bootstrap_hq" {
  secret_id                = aws_secretsmanager_secret.this["bootstrap-hq"].id
  secret_string_wo         = jsonencode({ email = var.hq_email, password = ephemeral.random_password.hq_password.result })
  secret_string_wo_version = 1
}

data "aws_region" "current" {}

resource "aws_sesv2_configuration_set" "this" {
  count                  = var.mail_from_address == "" && var.mail_domain == "" ? 0 : 1
  configuration_set_name = var.name

  delivery_options {
    tls_policy = "REQUIRE"
  }

  suppression_options {
    suppressed_reasons = ["BOUNCE", "COMPLAINT"]
  }
}

resource "aws_sesv2_email_identity" "sender" {
  count                  = var.mail_from_address == "" ? 0 : 1
  email_identity         = var.mail_from_address
  configuration_set_name = aws_sesv2_configuration_set.this[0].configuration_set_name
}

resource "aws_sesv2_email_identity" "domain" {
  count                  = var.mail_domain == "" ? 0 : 1
  email_identity         = var.mail_domain
  configuration_set_name = aws_sesv2_configuration_set.this[0].configuration_set_name

  dkim_signing_attributes {
    next_signing_key_length = "RSA_2048_BIT"
  }
}

resource "aws_sesv2_email_identity_mail_from_attributes" "domain" {
  count                  = var.mail_domain == "" ? 0 : 1
  email_identity         = aws_sesv2_email_identity.domain[0].email_identity
  mail_from_domain       = local.mail_from_domain
  behavior_on_mx_failure = "USE_DEFAULT_VALUE"
}

ephemeral "random_password" "secret_key" {
  length  = 64
  special = false
}

ephemeral "random_password" "mfa_key" {
  length           = 43
  special          = true
  override_special = "-_"
}

ephemeral "random_password" "hq_password" {
  length  = 24
  special = false
}

locals {
  secret_names = ["database-url", "secret-key", "mfa-encryption-key", "bootstrap-hq", "google-client-secret", "microsoft-client-secret", "yahoo-client-secret"]
}

resource "aws_secretsmanager_secret" "this" {
  for_each                = toset(local.secret_names)
  name                    = "bodha/${var.environment}/${each.key}"
  kms_key_id              = aws_kms_key.this.arn
  recovery_window_in_days = 7
}

resource "aws_secretsmanager_secret_version" "database_url" {
  secret_id                = aws_secretsmanager_secret.this["database-url"].id
  secret_string_wo         = "postgresql+asyncpg://bodha_app:${ephemeral.random_password.database.result}@${aws_db_instance.this.address}:5432/bodha?ssl=require"
  secret_string_wo_version = var.database_password_version

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

resource "aws_secretsmanager_secret_version" "bootstrap_hq" {
  secret_id                = aws_secretsmanager_secret.this["bootstrap-hq"].id
  secret_string_wo         = jsonencode({ email = var.hq_email, password = ephemeral.random_password.hq_password.result })
  secret_string_wo_version = 1
}

resource "aws_sesv2_configuration_set" "this" {
  count                  = var.mail_from_address == "" ? 0 : 1
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

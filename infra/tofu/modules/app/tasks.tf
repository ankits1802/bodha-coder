locals {
  app_url     = var.public_url == "" ? "https://${aws_cloudfront_distribution.this.domain_name}" : var.public_url
  api_image   = "${aws_ecr_repository.this["api"].repository_url}:${var.image_tag}"
  web_image   = "${aws_ecr_repository.this["web"].repository_url}:${var.image_tag}"
  legal_links = [for name, slug in { TERMS_URL = "terms", PRIVACY_URL = "privacy", BAA_URL = "baa" } : { name = name, value = "${local.app_url}/legal/${slug}" }]
  mail = length(var.ses_identity_arns) == 0 ? [
    { name = "EMAIL_TRANSPORT", value = "outbox" },
    { name = "MAIL_OUTBOX_DIR", value = "/tmp/outbox" },
    ] : [
    { name = "EMAIL_TRANSPORT", value = "ses" },
    { name = "MAIL_FROM", value = var.mail_from },
    { name = "SES_CONFIGURATION_SET", value = var.ses_configuration_set },
  ]
  shared_environment = concat([
    { name = "APP_ENVIRONMENT", value = var.environment },
    { name = "APP_URL", value = local.app_url },
    { name = "COOKIE_SECURE", value = "true" },
    { name = "AGREEMENT_VERSION", value = "1.0" },
    { name = "ADMIN_URL", value = var.admin_ready ? "https://${var.admin_host}" : "" },
    { name = "S3_BUCKET", value = var.bucket_name },
    { name = "S3_REGION", value = var.region },
    { name = "S3_SERVER_SIDE_ENCRYPTION", value = "" },
    { name = "SMS_TRANSPORT", value = var.sms_origination_number == "" ? "outbox" : "sns" },
    { name = "MAIL_OUTBOX_DIR", value = "/tmp/outbox" },
    { name = "AWS_MESSAGING_REGION", value = var.region },
    { name = "GEMINI_BACKEND", value = var.gemini_backend },
  ], var.sms_origination_number == "" ? [] : [{ name = "SNS_ORIGINATION_NUMBER", value = var.sms_origination_number }], local.legal_links, local.billing_environment, [for item in local.mail : item if item.name != "MAIL_OUTBOX_DIR"])
  stripe_on = length(var.billing.stripe_prices) > 0
  paypal_on = var.billing.paypal_client_id != ""
  billing_environment = concat(
    [for plan, id in var.billing.stripe_prices : { name = "STRIPE_PRICE_${upper(plan)}", value = id }],
    var.billing.stripe_portal_configuration == "" ? [] : [{ name = "STRIPE_PORTAL_CONFIGURATION", value = var.billing.stripe_portal_configuration }],
    [for plan, id in var.billing.paypal_plans : { name = "PAYPAL_PLAN_${upper(plan)}", value = id }],
    local.paypal_on ? [
      { name = "PAYPAL_CLIENT_ID", value = var.billing.paypal_client_id },
      { name = "PAYPAL_WEBHOOK_ID", value = var.billing.paypal_webhook_id },
      { name = "PAYPAL_ENVIRONMENT", value = var.billing.paypal_environment },
    ] : [],
  )
  billing_secrets = concat(
    local.stripe_on ? [
      { name = "STRIPE_SECRET_KEY", valueFrom = var.secret_arns["stripe-secret-key"] },
      { name = "STRIPE_WEBHOOK_SECRET", valueFrom = var.secret_arns["stripe-webhook-secret"] },
    ] : [],
    local.paypal_on ? [{ name = "PAYPAL_CLIENT_SECRET", valueFrom = var.secret_arns["paypal-client-secret"] }] : [],
  )
  identity_providers = {
    GOOGLE    = { id = var.google_client_id, secret = "google-client-secret" }
    MICROSOFT = { id = var.microsoft_client_id, secret = "microsoft-client-secret" }
    YAHOO     = { id = var.yahoo_client_id, secret = "yahoo-client-secret" }
  }
  identity_environment = [for prefix, provider in local.identity_providers : { name = "${prefix}_CLIENT_ID", value = provider.id } if provider.id != ""]
  identity_secrets     = [for prefix, provider in local.identity_providers : { name = "${prefix}_CLIENT_SECRET", valueFrom = var.secret_arns[provider.secret] } if provider.id != ""]
  shared_secrets = concat([
    { name = "DATABASE_URL", valueFrom = var.secret_arns["database-url"] },
    { name = "SECRET_KEY", valueFrom = var.secret_arns["secret-key"] },
  ], var.gemini_backend == "developer" ? [{ name = "GEMINI_API_KEY", valueFrom = var.secret_arns["gemini-api-key"] }] : [], local.billing_secrets)
  tasks = {
    api = {
      image   = local.api_image
      command = ["api"]
      cpu     = 256
      memory  = 1024
      role    = aws_iam_role.app.arn
      port    = 8000
      stop    = 30
      environment = concat(local.shared_environment, local.identity_environment, [
        { name = "FORWARDED_ALLOW_IPS", value = var.vpc_cidr },
        { name = "WEB_CONCURRENCY", value = "1" },
      ])
      secrets = concat(local.shared_secrets, local.identity_secrets, [
        { name = "MFA_ENCRYPTION_KEY", valueFrom = var.secret_arns["mfa-encryption-key"] },
      ])
    }
    worker = {
      image       = local.api_image
      command     = ["worker"]
      cpu         = 256
      memory      = 1024
      role        = aws_iam_role.app.arn
      port        = null
      stop        = 120
      environment = local.shared_environment
      secrets     = local.shared_secrets
    }
    migrate = {
      image       = local.api_image
      command     = ["migrate"]
      cpu         = 256
      memory      = 512
      role        = aws_iam_role.plain.arn
      port        = null
      stop        = 30
      environment = local.shared_environment
      secrets     = local.shared_secrets
    }
    bootstrap = {
      image       = local.api_image
      command     = ["python", "-m", "app.scripts.bootstrap_hq"]
      cpu         = 256
      memory      = 512
      role        = aws_iam_role.plain.arn
      port        = null
      stop        = 30
      environment = local.shared_environment
      secrets = concat(local.shared_secrets, [
        { name = "BOOTSTRAP_HQ_EMAIL", valueFrom = "${var.secret_arns["bootstrap-hq"]}:email::" },
        { name = "BOOTSTRAP_HQ_PASSWORD", valueFrom = "${var.secret_arns["bootstrap-hq"]}:password::" },
      ])
    }
    web = {
      image       = local.web_image
      command     = null
      cpu         = 256
      memory      = 512
      role        = aws_iam_role.plain.arn
      port        = 3000
      stop        = 30
      environment = [{ name = "BACKEND_URL", value = "http://${aws_lb.this.dns_name}" }, { name = "SITE_URL", value = local.app_url }, { name = "ADMIN_URL", value = var.admin_ready ? "https://${var.admin_host}" : "" }]
      secrets     = []
    }
  }
}

resource "aws_cloudwatch_log_group" "this" {
  for_each          = local.tasks
  name              = "/${var.name}/${each.key}"
  retention_in_days = 2557
}

resource "aws_ecs_task_definition" "this" {
  for_each                 = local.tasks
  family                   = "${var.name}-${each.key}"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = each.value.cpu
  memory                   = each.value.memory
  execution_role_arn       = aws_iam_role.execution.arn
  task_role_arn            = each.value.role

  runtime_platform {
    operating_system_family = "LINUX"
    cpu_architecture        = "X86_64"
  }

  container_definitions = jsonencode([{
    name         = each.key
    image        = each.value.image
    essential    = true
    command      = each.value.command
    stopTimeout  = each.value.stop
    environment  = each.value.environment
    secrets      = each.value.secrets
    portMappings = each.value.port == null ? [] : [{ containerPort = each.value.port, protocol = "tcp" }]
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        awslogs-group         = aws_cloudwatch_log_group.this[each.key].name
        awslogs-region        = var.region
        awslogs-stream-prefix = each.key
      }
    }
  }])
}

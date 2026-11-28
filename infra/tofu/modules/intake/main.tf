locals {
  function_name = "${var.name}-ses-intake"
  rule_set_name = "${var.name}-intake"
  rule_name     = "${var.name}-intake"
  rule_arn      = "arn:aws:ses:${var.region}:${var.account_id}:receipt-rule-set/${local.rule_set_name}:receipt-rule/${local.rule_name}"
  inbound       = "ses-inbound/"
}

data "archive_file" "function" {
  type        = "zip"
  source_file = var.source_file
  output_path = "${path.root}/.terraform/ses-intake.zip"
}

data "aws_iam_policy_document" "function_trust" {
  statement {
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }

    condition {
      test     = "StringEquals"
      variable = "aws:SourceAccount"
      values   = [var.account_id]
    }
  }
}

resource "aws_iam_role" "function" {
  name               = local.function_name
  assume_role_policy = data.aws_iam_policy_document.function_trust.json
}

resource "aws_cloudwatch_log_group" "function" {
  name              = "/aws/lambda/${local.function_name}"
  retention_in_days = var.retention_days
}

data "aws_iam_policy_document" "function" {
  statement {
    sid       = "Logs"
    actions   = ["logs:CreateLogStream", "logs:PutLogEvents"]
    resources = ["${aws_cloudwatch_log_group.function.arn}:*"]
  }

  statement {
    sid       = "Envelopes"
    actions   = ["s3:PutObject"]
    resources = ["${aws_s3_bucket.inbound.arn}/${local.inbound}*.json"]
  }

  statement {
    sid       = "DocumentKey"
    actions   = ["kms:GenerateDataKey"]
    resources = [var.kms_key_arn]
  }
}

resource "aws_iam_role_policy" "function" {
  name   = "ses-intake"
  role   = aws_iam_role.function.id
  policy = data.aws_iam_policy_document.function.json
}

resource "aws_lambda_function" "this" {
  function_name    = local.function_name
  role             = aws_iam_role.function.arn
  runtime          = "python3.14"
  architectures    = ["arm64"]
  handler          = "handler.handler"
  filename         = data.archive_file.function.output_path
  source_code_hash = data.archive_file.function.output_base64sha256
  timeout          = 30
  memory_size      = 128

  environment {
    variables = {
      INTAKE_BUCKET = aws_s3_bucket.inbound.bucket
    }
  }

  logging_config {
    log_format = "Text"
    log_group  = aws_cloudwatch_log_group.function.name
  }

  depends_on = [aws_iam_role_policy.function]
}

resource "aws_lambda_permission" "ses" {
  statement_id   = "ses-intake"
  action         = "lambda:InvokeFunction"
  function_name  = aws_lambda_function.this.function_name
  principal      = "ses.amazonaws.com"
  source_account = var.account_id
  source_arn     = local.rule_arn
}

data "aws_iam_policy_document" "receipt_trust" {
  statement {
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["ses.amazonaws.com"]
    }

    condition {
      test     = "StringEquals"
      variable = "aws:SourceAccount"
      values   = [var.account_id]
    }

    condition {
      test     = "StringEquals"
      variable = "aws:SourceArn"
      values   = [local.rule_arn]
    }
  }
}

resource "aws_iam_role" "receipt" {
  name               = "${var.name}-ses-receipt"
  assume_role_policy = data.aws_iam_policy_document.receipt_trust.json
}

data "aws_iam_policy_document" "receipt" {
  statement {
    sid       = "StoreMail"
    actions   = ["s3:PutObject"]
    resources = ["${aws_s3_bucket.inbound.arn}/${local.inbound}*"]
  }

  statement {
    sid       = "DocumentKey"
    actions   = ["kms:GenerateDataKey", "kms:Decrypt"]
    resources = [var.kms_key_arn]
  }
}

resource "aws_iam_role_policy" "receipt" {
  name   = "ses-receipt"
  role   = aws_iam_role.receipt.id
  policy = data.aws_iam_policy_document.receipt.json
}

resource "aws_ses_receipt_rule_set" "this" {
  rule_set_name = local.rule_set_name
}

resource "aws_ses_receipt_rule" "this" {
  name          = local.rule_name
  rule_set_name = aws_ses_receipt_rule_set.this.rule_set_name
  recipients    = [var.domain]
  enabled       = true
  scan_enabled  = true
  tls_policy    = "Require"

  s3_action {
    position          = 1
    bucket_name       = aws_s3_bucket.inbound.bucket
    object_key_prefix = local.inbound
    iam_role_arn      = aws_iam_role.receipt.arn
  }

  lambda_action {
    position        = 2
    function_arn    = aws_lambda_function.this.arn
    invocation_type = "Event"
  }

  depends_on = [aws_lambda_permission.ses, aws_iam_role_policy.receipt, aws_s3_bucket_policy.inbound]
}

resource "aws_ses_active_receipt_rule_set" "this" {
  count         = var.live ? 1 : 0
  rule_set_name = aws_ses_receipt_rule_set.this.rule_set_name

  depends_on = [aws_ses_receipt_rule.this]
}

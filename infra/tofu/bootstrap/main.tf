terraform {
  required_version = "1.13.10"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "6.74.0"
    }
  }

  backend "s3" {
    key          = "bootstrap/terraform.tfstate"
    region       = "us-east-1"
    encrypt      = true
    use_lockfile = true
  }
}

variable "account_id" {
  type = string
}

variable "region" {
  type    = string
  default = "us-east-1"
}

variable "operator_user" {
  type = string
}

provider "aws" {
  region              = var.region
  allowed_account_ids = [var.account_id]

  default_tags {
    tags = {
      Project   = "bodha-coder"
      Stack     = "bootstrap"
      ManagedBy = "opentofu"
    }
  }
}

resource "aws_s3_bucket" "state" {
  bucket = "bodha-tofu-state-${var.account_id}"
}

resource "aws_s3_bucket_ownership_controls" "state" {
  bucket = aws_s3_bucket.state.id

  rule {
    object_ownership = "BucketOwnerEnforced"
  }
}

resource "aws_s3_bucket_public_access_block" "state" {
  bucket                  = aws_s3_bucket.state.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_versioning" "state" {
  bucket = aws_s3_bucket.state.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "state" {
  bucket = aws_s3_bucket.state.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "state" {
  bucket = aws_s3_bucket.state.id

  rule {
    id     = "old-versions"
    status = "Enabled"

    filter {}

    noncurrent_version_expiration {
      noncurrent_days = 90
    }
  }
}

data "aws_iam_policy_document" "state" {
  statement {
    sid       = "TlsOnly"
    effect    = "Deny"
    actions   = ["s3:*"]
    resources = [aws_s3_bucket.state.arn, "${aws_s3_bucket.state.arn}/*"]

    principals {
      type        = "*"
      identifiers = ["*"]
    }

    condition {
      test     = "Bool"
      variable = "aws:SecureTransport"
      values   = ["false"]
    }
  }
}

resource "aws_s3_bucket_policy" "state" {
  bucket = aws_s3_bucket.state.id
  policy = data.aws_iam_policy_document.state.json
}

data "aws_iam_policy_document" "edge" {
  statement {
    sid = "CloudFront"
    actions = [
      "cloudfront:CreateDistribution",
      "cloudfront:UpdateDistribution",
      "cloudfront:DeleteDistribution",
      "cloudfront:GetDistribution",
      "cloudfront:GetDistributionConfig",
      "cloudfront:ListDistributions",
      "cloudfront:CreateVpcOrigin",
      "cloudfront:UpdateVpcOrigin",
      "cloudfront:DeleteVpcOrigin",
      "cloudfront:GetVpcOrigin",
      "cloudfront:ListVpcOrigins",
      "cloudfront:GetCachePolicy",
      "cloudfront:ListCachePolicies",
      "cloudfront:GetOriginRequestPolicy",
      "cloudfront:ListOriginRequestPolicies",
      "cloudfront:CreateInvalidation",
      "cloudfront:GetInvalidation",
      "cloudfront:TagResource",
      "cloudfront:UntagResource",
      "cloudfront:ListTagsForResource",
    ]
    resources = ["*"]
  }

  statement {
    sid = "Ses"
    actions = [
      "ses:CreateEmailIdentity",
      "ses:DeleteEmailIdentity",
      "ses:GetEmailIdentity",
      "ses:ListEmailIdentities",
      "ses:PutEmailIdentityConfigurationSetAttributes",
      "ses:CreateConfigurationSet",
      "ses:DeleteConfigurationSet",
      "ses:GetConfigurationSet",
      "ses:ListConfigurationSets",
      "ses:PutConfigurationSetSuppressionOptions",
      "ses:PutConfigurationSetDeliveryOptions",
      "ses:PutConfigurationSetReputationOptions",
      "ses:PutConfigurationSetSendingOptions",
      "ses:PutEmailIdentityMailFromAttributes",
      "ses:PutEmailIdentityDkimAttributes",
      "ses:PutEmailIdentityDkimSigningAttributes",
      "ses:PutEmailIdentityFeedbackAttributes",
      "ses:GetAccount",
      "ses:PutAccountDetails",
      "ses:TagResource",
      "ses:UntagResource",
      "ses:ListTagsForResource",
    ]
    resources = ["*"]
  }

  statement {
    sid = "Certificates"
    actions = [
      "acm:RequestCertificate",
      "acm:DescribeCertificate",
      "acm:DeleteCertificate",
      "acm:ListCertificates",
      "acm:AddTagsToCertificate",
      "acm:RemoveTagsFromCertificate",
      "acm:ListTagsForCertificate",
    ]
    resources = ["*"]
  }

  statement {
    sid = "HealthChecks"
    actions = [
      "route53:CreateHealthCheck",
      "route53:UpdateHealthCheck",
      "route53:DeleteHealthCheck",
      "route53:GetHealthCheck",
      "route53:GetHealthCheckStatus",
      "route53:ListHealthChecks",
      "route53:ChangeTagsForResource",
      "route53:ListTagsForResource",
    ]
    resources = ["*"]
  }

  statement {
    sid = "CostTags"
    actions = [
      "ce:ListCostAllocationTags",
      "ce:UpdateCostAllocationTagsStatus",
    ]
    resources = ["*"]
  }

  statement {
    sid = "Backups"
    actions = [
      "backup:CreateBackupVault",
      "backup:DeleteBackupVault",
      "backup:DescribeBackupVault",
      "backup:ListBackupVaults",
      "backup:PutBackupVaultLockConfiguration",
      "backup:DeleteBackupVaultLockConfiguration",
      "backup:PutBackupVaultAccessPolicy",
      "backup:GetBackupVaultAccessPolicy",
      "backup:DeleteBackupVaultAccessPolicy",
      "backup:CreateBackupPlan",
      "backup:UpdateBackupPlan",
      "backup:DeleteBackupPlan",
      "backup:GetBackupPlan",
      "backup:ListBackupPlans",
      "backup:ListBackupPlanVersions",
      "backup:CreateBackupSelection",
      "backup:DeleteBackupSelection",
      "backup:GetBackupSelection",
      "backup:ListBackupSelections",
      "backup:TagResource",
      "backup:UntagResource",
      "backup:ListTags",
      "backup-storage:MountCapsule",
    ]
    resources = ["*"]
  }

  statement {
    sid = "Trail"
    actions = [
      "cloudtrail:CreateTrail",
      "cloudtrail:UpdateTrail",
      "cloudtrail:DeleteTrail",
      "cloudtrail:GetTrail",
      "cloudtrail:GetTrailStatus",
      "cloudtrail:StartLogging",
      "cloudtrail:StopLogging",
      "cloudtrail:PutEventSelectors",
      "cloudtrail:GetEventSelectors",
      "cloudtrail:AddTags",
      "cloudtrail:RemoveTags",
      "cloudtrail:ListTags",
    ]
    resources = ["arn:aws:cloudtrail:${var.region}:${var.account_id}:trail/bodha-*"]
  }

  statement {
    sid       = "TrailRead"
    actions   = ["cloudtrail:DescribeTrails", "cloudtrail:ListTrails"]
    resources = ["*"]
  }

  statement {
    sid = "Budgets"
    actions = [
      "budgets:ModifyBudget",
      "budgets:ViewBudget",
      "budgets:TagResource",
      "budgets:UntagResource",
      "budgets:ListTagsForResource",
    ]
    resources = ["arn:aws:budgets::${var.account_id}:budget/bodha-*"]
  }
}

resource "aws_iam_policy" "edge" {
  name        = "bodha-staging-edge"
  description = "CloudFront, SES and budget actions for the Bodha Coder staging stack"
  policy      = data.aws_iam_policy_document.edge.json
}

resource "aws_iam_user_policy_attachment" "edge" {
  user       = var.operator_user
  policy_arn = aws_iam_policy.edge.arn
}

output "state_bucket" {
  value = aws_s3_bucket.state.bucket
}

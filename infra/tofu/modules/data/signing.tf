resource "aws_kms_key" "signing" {
  description              = "${var.name} seals signed records"
  customer_master_key_spec = "ECC_NIST_P256"
  key_usage                = "SIGN_VERIFY"
  deletion_window_in_days  = 30
  policy                   = data.aws_iam_policy_document.key.json
}

resource "aws_kms_alias" "signing" {
  name          = "alias/${var.name}-signing"
  target_key_id = aws_kms_key.signing.key_id
}

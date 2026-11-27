# Automatic intake: how a practice drops files

Bodha reads PDFs that a practice places in its own inbox prefix, about once a minute. How the
inbox is read is in [ARCHITECTURE.md](ARCHITECTURE.md#intake); the decision is
[0017](decisions/0017-remittance-intake-query-governance.md).

## The inbox

```
s3://<bucket>/practices/<practice id>/inbox/<provider folder>/<YYYY-MM-DD>/<file>.pdf
```

| Part | Rule |
|---|---|
| practice id | shown as the watched folder in Practice setup, Automatic intake |
| provider folder | a name the admin maps to a provider there (letters, digits, `.`, `-`, `_`); `processed` and `rejected` are reserved |
| `YYYY-MM-DD` | the date of service; a future date is refused |
| file | a PDF. The billed CPT can be in the name as in a manual upload (`2026-11-20 - 99214 - Progress.pdf`). Name files without patient details (no names, dates of birth or record numbers): Bodha reads the patient from the note. The first poll that sees a file, about a minute after it lands, renames it to the SHA-256 of its content (`<sha256> - 99214.pdf` keeps a CPT code from the name), so a name lives at most one poll, and only the new name reaches the note and the reason files |

The admin turns intake on with a place of service, a visit type and at least one provider folder.
Every file is then moved out of the inbox: notes to `inbox/processed/<day>/`, everything else to
`inbox/rejected/<day>/` beside a `.reason.txt` that names the path (after renaming) and the reason.
Each batch appears in Upload history as uploaded by Intake, and the access log records the upload by
Bodha intake.

The inbox holds PHI and must stay private: Block Public Access stays on, no bucket policy, ACL,
access point or presigned link may grant reading it, and only the practice's own principal (below)
and Bodha's task roles reach it.

## Access for the practice

Give each practice its own principal that can write only its inbox and read only its results:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    { "Effect": "Allow", "Action": "s3:PutObject",
      "Resource": "arn:aws:s3:::<bucket>/practices/<practice id>/inbox/*" },
    { "Effect": "Allow", "Action": "s3:GetObject",
      "Resource": "arn:aws:s3:::<bucket>/practices/<practice id>/inbox/rejected/*" },
    { "Effect": "Allow", "Action": "s3:ListBucket", "Resource": "arn:aws:s3:::<bucket>",
      "Condition": { "StringLike": { "s3:prefix": "practices/<practice id>/inbox/*" } } },
    { "Effect": "Allow", "Action": ["kms:GenerateDataKey", "kms:Decrypt"], "Resource": "<bucket KMS key ARN>" }
  ]
}
```

The bucket's default SSE-KMS encryption applies to every dropped object; the bucket policy in
[DEPLOY.md](DEPLOY.md#object-storage-s3) already refuses plain-text transport and `AES256`.

## Option 1: S3 sync from the practice

For a practice with a scanner or EHR export folder on a workstation or server:

```
aws s3 sync "D:\Scans\Bodha" s3://<bucket>/practices/<practice id>/inbox/ --exclude "*" --include "*.pdf"
```

Run it from a scheduled task every few minutes with the practice's credentials (an IAM user's
access key kept in the AWS CLI profile, or IAM Roles Anywhere). Keep the local folder in the
`<provider folder>/<YYYY-MM-DD>/` layout and clear it after a successful sync, so a file is not
sent again: the inbox renames what arrives, so `sync` cannot see that a file was already sent, and a
second copy of the same PDF is rejected as already uploaded.

## Option 2: SFTP through AWS Transfer Family

For a practice whose EHR or scanning vendor can only send by SFTP:

1. Create a Transfer Family SFTP server with the S3 domain, a VPC or public endpoint, and the
   security policy `TransferSecurityPolicy-2024-01` or newer.
2. Add one service-managed user per practice with its SSH public key, a role holding the policy
   above, and a logical home directory mapping `/` to
   `/<bucket>/practices/<practice id>/inbox`, so the practice sees only its inbox.
3. The vendor uploads to `/<provider folder>/<YYYY-MM-DD>/<file>.pdf`.

Transfer Family is HIPAA eligible under the AWS BAA; turn on its CloudWatch logging.

## Option 3: email to an inbound address

For a practice that can only email documents, with the function in
[infra/ses_intake](../infra/ses_intake/README.md) (receipt rule, bucket and key policy, role and
deployment are there).

1. Verify a receiving domain in SES (for example `intake.<your domain>`) with an MX record to the
   SES inbound endpoint of the region.
2. Add a receipt rule for each practice address (for example `lakeside-varga@intake.<your domain>`,
   one address per provider folder) with Require TLS and spam and virus scanning on, and an S3
   action that saves the raw message under `ses-inbound/<local part>/`, outside `practices/`.
3. Map the address in the function's `INTAKE_ADDRESSES` to the practice id, the provider folder and
   the senders allowed to use it.
4. The practice emails the PDFs with the date of service in the subject (`YYYY-MM-DD`). The function
   refuses a message SES did not pass for spam and viruses, a sender not on the list or a subject
   without a date; otherwise it writes each PDF attachment to
   `practices/<practice id>/inbox/<provider folder>/<YYYY-MM-DD>/<sha256>.pdf`. It keeps every raw
   message under `ses-retained/<local part>/` before reading it, then removes it from `ses-inbound/`,
   and logs outcomes and counts only. Billed codes are not read from attachment
   names.

Email between the practice and SES is only as private as the practice's mail server's TLS; prefer
options 1 or 2 when the practice can use them.

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
| practice id | the practice's id, known to Bodha's operators; Settings, Setup, Automatic intake tells the practice only whether its PDFs are being read, never the storage path ([0041](decisions/0041-streamlined-navigation-and-first-day.md)) |
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

## Option 3: email to the practice's own address

For a practice that can only email or forward documents ([0045](decisions/0045-email-intake.md)). Bodha
runs it; the practice needs no AWS access.

1. Bodha's operator applies email intake once for every practice (`email_intake_subdomain`, the MX record,
   then `email_intake_live`: [infra/tofu/README.md](../infra/tofu/README.md#email-intake)).
2. The admin opens Settings, Setup, Automatic intake, chooses Get an address and copies it. New address
   replaces it (the old one stops working and stays in Earlier addresses); Turn off retires it.
3. The admin adds the allowed senders: each scanner or person's address, or the practice's whole domain.
   A public mail service such as gmail.com can only be allowed address by address.
4. Send a test emails the address from Bodha and shows when it arrived. Then send one note from the
   scanner and check Received.
5. The practice emails or forwards PDFs to the address. Each PDF must show the provider (name or NPI) and
   the date of service on page 1 clearly enough, as for a drop upload; the billed CPT can be in the file
   name. The place of service is read from page 1, else the provider's usual place, else the place set
   for intake above; the visit type is the one set for intake.

Mail is refused, recorded and never read when it goes to an earlier address, when SES did not pass it
for spam and viruses, when the sender's domain does not pass DMARC (a domain without a DMARC record is
"sender not verified"; publish one), when the sender is not allowed, when it carries no PDF or more than
50 files, or while the practice is not open. Forwarding by hand from an allowed mailbox works; a server
rule that forwards mail on with the original sender usually fails DMARC. Each message appears in Received
with its time, sender and outcome, and each refused file with its reason; subjects, bodies and file names
are never shown or stored. Accepted notes appear in Upload history as uploaded by Intake.

Email between the practice and Bodha is protected by TLS, which SES requires of the sending server;
prefer options 1 or 2 when the practice can use them.

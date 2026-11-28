# Email intake function

`handler.py` is the AWS Lambda function of email intake (Python 3.14, standard library and the `boto3`
the runtime provides; nothing is vendored). OpenTofu packages and deploys it with the receipt rule
(`infra/tofu/modules/intake`); nothing here is deployed by hand. Decision:
[0046](../../docs/decisions/0046-email-intake.md).

SES receives mail for the intake domain (for example `intake.bodhaai.co`) with one receipt rule:
TLS required, spam and virus scanning on, then two actions in order.

1. **S3:** the raw message is stored at `ses-inbound/<message id>` in the inbound mail bucket
   `bodha-staging-mail-inbound-<account>`, through the role `bodha-staging-ses-receipt`, under the
   documents key. SES cannot write into the documents bucket, whose Object Lock has a default retention;
   the worker keeps every message there under `ses-retained/` and then deletes the inbound copy.
2. **Lambda** (`Event`): the function writes `ses-inbound/<message id>.json`:

```json
{
  "message_id": "o3vrnil0e2ic28trm7dfhrc2v0clambda4nbp0g01",
  "received_at": "2026-11-28T10:15:00.000Z",
  "recipients": ["k3j8w2q9x7m4n5p6@intake.bodhaai.co"],
  "verdicts": { "dkim": "PASS", "dmarc": "PASS", "spam": "PASS", "spf": "PASS", "virus": "PASS" },
  "version": 1
}
```

The recipients are the envelope recipients SES matched, lowercased; a verdict SES did not give is
blank, never `PASS`. A message id other than letters, digits, dashes and underscores is refused. The
function reads no mail and decides nothing: the worker (`services.email_intake`) reads the envelope and
the message, keeps the message under `ses-retained/`, checks the address, the verdicts and the sender,
uploads the PDFs and records the outcome, then deletes both objects from `ses-inbound/`.

It logs one line per message: `{"event": "ses intake", "message": "<message id>", "recipients": <count>}`.
It never logs addresses, names, subjects or file names.

## Configuration

| Variable | Value |
|---|---|
| `INTAKE_BUCKET` | the inbound mail bucket, `bodha-staging-mail-inbound-<account>` |

## Permissions

| Principal | May |
|---|---|
| function role `bodha-staging-ses-intake` | `s3:PutObject` on `ses-inbound/*.json` in the inbound bucket, `kms:GenerateDataKey` on the documents key, write its log group `/aws/lambda/bodha-staging-ses-intake` (kept 2557 days) |
| receipt role `bodha-staging-ses-receipt` | assumed only by `ses.amazonaws.com` for this account's intake rule; `s3:PutObject` on `ses-inbound/*` in the inbound bucket, `kms:GenerateDataKey` and `kms:Decrypt` on the documents key |
| `ses.amazonaws.com` | invoke the function, for this account's intake rule only |

The bucket policy and the key policy are unchanged. Lambda, SES and S3 are HIPAA eligible under the AWS
BAA. Tests: `backend/tests/infra/test_ses_intake.py` (including the worker reading what the function
writes).

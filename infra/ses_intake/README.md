# Email intake function

`handler.py` is an AWS Lambda function (Python 3.14, standard library and the `boto3` the runtime
provides; nothing is vendored). SES stores each message sent to a practice's intake address in the
documents bucket under `ses-inbound/<recipient>/`; the bucket notifies the function, which:

1. reads the raw message and takes the recipient from its key (`ses-inbound/<recipient>/<message id>`);
2. looks the recipient up in `INTAKE_ADDRESSES`;
3. refuses the message unless SES marked it `PASS` for spam and viruses and its single `From` address
   is one of that inbox's `senders`;
4. takes the date of service from the subject (`YYYY-MM-DD`); without one nothing is written;
5. writes every PDF attachment (content type `application/pdf` or a `.pdf` name, and the `%PDF`
   signature) to `practices/<practice id>/<inbox>/<provider folder>/<YYYY-MM-DD>/<sha256>.pdf`, where
   the intake poller picks it up; other attachments are ignored;
6. deletes the raw message, whether or not anything was written.

It logs one line per message with the outcome (`delivered`, `no_pdf`, `no_date`, `sender_refused`,
`verdict_failed`, `unknown_recipient`), the practice id and the number of files written. It never logs
addresses, names, subjects or file names. Billed codes are not read from attachment names; a future
date or an unmapped folder is refused by the poller, which explains it in `rejected/`.

How the inbox is read: [DEPLOY-INTAKE.md](../../docs/DEPLOY-INTAKE.md).

## Configuration

| Variable | Value |
|---|---|
| `INTAKE_ADDRESSES` | JSON mapping each recipient local part to its inbox, for example `{"lakeside-varga": {"practice": "<practice id>", "folder": "varga", "senders": ["scans@lakeside.example.com"]}}`; `inbox` is optional (`inbox` or `inbox-…`, the practice's watched folder) |

A recipient, sender list or folder that is missing or malformed stops the function before it reads
anything. Encrypt the environment with a customer managed key.

## SES receipt rule

Verify the receiving domain (for example `intake.<your domain>`) and point its MX record at the SES
inbound endpoint of the region. In the active receipt rule set, add one rule per practice address:

```json
{
  "Name": "intake-lakeside-varga",
  "Enabled": true,
  "TlsPolicy": "Require",
  "ScanEnabled": true,
  "Recipients": ["lakeside-varga@intake.example.com"],
  "Actions": [
    {
      "S3Action": {
        "BucketName": "<bucket>",
        "ObjectKeyPrefix": "ses-inbound/lakeside-varga/"
      }
    },
    { "StopAction": { "Scope": "RuleSet" } }
  ]
}
```

```
aws ses create-receipt-rule --rule-set-name bodha-intake --rule file://rule.json
```

Leave the S3 action's own encryption off: the bucket's default SSE-KMS key encrypts the stored
message, and the function reads it with an ordinary `GetObject`.

## Bucket

Add these statements to the bucket policy in [DEPLOY.md](../../docs/DEPLOY.md#object-storage-s3):

```json
{
  "Sid": "SesStoresIntakeMail",
  "Effect": "Allow",
  "Principal": { "Service": "ses.amazonaws.com" },
  "Action": "s3:PutObject",
  "Resource": "arn:aws:s3:::<bucket>/ses-inbound/*",
  "Condition": {
    "StringEquals": { "aws:SourceAccount": "<account id>" },
    "ArnLike": { "aws:SourceArn": "arn:aws:ses:<region>:<account id>:receipt-rule-set/bodha-intake:receipt-rule/*" }
  }
}
```

and to the bucket key's policy:

```json
{
  "Sid": "SesEncryptsIntakeMail",
  "Effect": "Allow",
  "Principal": { "Service": "ses.amazonaws.com" },
  "Action": ["kms:GenerateDataKey", "kms:Decrypt"],
  "Resource": "*",
  "Condition": {
    "StringEquals": { "aws:SourceAccount": "<account id>", "kms:ViaService": "s3.<region>.amazonaws.com" }
  }
}
```

Add a lifecycle rule that expires current objects under `ses-inbound/` after 1 day, so a message the
function could not handle does not stay.

## Function role

The execution role holds only this policy and `AWSLambdaBasicExecutionRole` for its log group. List
each mapped practice's watched folder (`inbox` or its `inbox-…`); do not use a wildcard for the practice
id.

```json
{
  "Version": "2012-10-17",
  "Statement": [
    { "Effect": "Allow", "Action": ["s3:GetObject", "s3:DeleteObject"],
      "Resource": "arn:aws:s3:::<bucket>/ses-inbound/*" },
    { "Effect": "Allow", "Action": "s3:PutObject",
      "Resource": ["arn:aws:s3:::<bucket>/practices/<practice id>/inbox/*"] },
    { "Effect": "Allow", "Action": ["kms:Decrypt", "kms:GenerateDataKey"],
      "Resource": "<bucket KMS key ARN>" }
  ]
}
```

## Deploy

```
cd infra/ses_intake
python -c "import zipfile; zipfile.ZipFile('function.zip', 'w').write('handler.py')"
aws logs create-log-group --log-group-name /aws/lambda/bodha-ses-intake --kms-key-id <logs key ARN>
aws logs put-retention-policy --log-group-name /aws/lambda/bodha-ses-intake --retention-in-days 400
aws lambda create-function --function-name bodha-ses-intake --runtime python3.14 --architectures arm64 \
  --handler handler.handler --zip-file fileb://function.zip --role <execution role ARN> \
  --timeout 60 --memory-size 512 --kms-key-arn <key ARN> \
  --environment "Variables={INTAKE_ADDRESSES=<json>}"
aws lambda add-permission --function-name bodha-ses-intake --statement-id s3-intake \
  --action lambda:InvokeFunction --principal s3.amazonaws.com \
  --source-arn arn:aws:s3:::<bucket> --source-account <account id>
aws s3api put-bucket-notification-configuration --bucket <bucket> --notification-configuration file://notification.json
```

`notification.json` (this call replaces the bucket's whole notification configuration, so merge it with
any existing one):

```json
{
  "LambdaFunctionConfigurations": [
    {
      "LambdaFunctionArn": "<function ARN>",
      "Events": ["s3:ObjectCreated:*"],
      "Filter": { "Key": { "FilterRules": [{ "Name": "prefix", "Value": "ses-inbound/" }] } }
    }
  ]
}
```

Update the code with `aws lambda update-function-code --function-name bodha-ses-intake --zip-file fileb://function.zip`
and a mapping with `aws lambda update-function-configuration --function-name bodha-ses-intake --environment …`.
Lambda, SES and S3 are HIPAA eligible under the AWS BAA. Tests: `backend/tests/infra/test_ses_intake.py`.

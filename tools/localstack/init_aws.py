import os
from email.utils import parseaddr
from typing import Any

import boto3
from botocore.exceptions import ClientError

ENDPOINT = "http://localhost:4566"
LOCAL_CREDENTIALS = {"aws_access_key_id": "test", "aws_secret_access_key": "test"}
DEFAULT_REGION = "us-east-1"
DEFAULT_ENCRYPTION = {"Rules": [{"ApplyServerSideEncryptionByDefault": {"SSEAlgorithm": "AES256"}}]}


def local_client(service: str, region: str) -> Any:
    return boto3.client(service, endpoint_url=ENDPOINT, region_name=region, **LOCAL_CREDENTIALS)


def create_bucket(name: str, region: str) -> None:
    s3 = local_client("s3", region)
    location = {} if region == DEFAULT_REGION else {"CreateBucketConfiguration": {"LocationConstraint": region}}
    s3.create_bucket(Bucket=name, **location)
    s3.put_public_access_block(
        Bucket=name,
        PublicAccessBlockConfiguration={
            "BlockPublicAcls": True,
            "IgnorePublicAcls": True,
            "BlockPublicPolicy": True,
            "RestrictPublicBuckets": True,
        },
    )
    s3.put_bucket_versioning(Bucket=name, VersioningConfiguration={"Status": "Enabled"})
    s3.put_bucket_encryption(Bucket=name, ServerSideEncryptionConfiguration=DEFAULT_ENCRYPTION)


def verify_sender(mail_from: str, region: str) -> None:
    address = parseaddr(mail_from)[1]
    if "@" not in address:
        raise ValueError(f"MAIL_FROM has no sender address: {mail_from!r}")
    try:
        local_client("sesv2", region).create_email_identity(EmailIdentity=address)
    except ClientError as error:
        if error.response.get("Error", {}).get("Code") != "AlreadyExistsException":
            raise


def prepare(environment: dict[str, str]) -> None:
    region = environment["AWS_MESSAGING_REGION"]
    create_bucket(environment["S3_BUCKET"], environment["S3_REGION"])
    verify_sender(environment["MAIL_FROM"], region)


prepare(dict(os.environ))

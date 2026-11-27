from datetime import UTC, datetime

import boto3
import pytest
from botocore.stub import Stubber

from app.adapters.object_listing import S3ListingStore, StoredObject
from app.core.config import get_settings

BUCKET = "bodha-test"
PREFIX = "practices/p-1/"
FIRST = datetime(2026, 11, 20, 8, 30, tzinfo=UTC)
SECOND = datetime(2026, 11, 26, 17, 5, tzinfo=UTC)


def _client():
    return boto3.client("s3", region_name="us-east-1", aws_access_key_id="testing", aws_secret_access_key="testing")


def _store(client) -> S3ListingStore:
    return S3ListingStore(get_settings().model_copy(update={"s3_bucket": BUCKET}), client=client)


async def test_objects_are_listed_page_by_page_with_their_times():
    client = _client()
    with Stubber(client) as stub:
        stub.add_response(
            "list_objects_v2",
            {
                "Contents": [{"Key": f"{PREFIX}notes/n-1/document.pdf", "LastModified": FIRST}],
                "IsTruncated": True,
                "NextContinuationToken": "page-2",
            },
            {"Bucket": BUCKET, "Prefix": PREFIX},
        )
        stub.add_response(
            "list_objects_v2",
            {"Contents": [{"Key": f"{PREFIX}remittances/r-1.835", "LastModified": SECOND}], "IsTruncated": False},
            {"Bucket": BUCKET, "Prefix": PREFIX, "ContinuationToken": "page-2"},
        )
        pages = [page async for page in _store(client).object_pages(PREFIX)]
        stub.assert_no_pending_responses()
    assert pages == [
        [StoredObject(f"{PREFIX}notes/n-1/document.pdf", FIRST)],
        [StoredObject(f"{PREFIX}remittances/r-1.835", SECOND)],
    ]


async def test_folders_are_the_common_prefixes_under_a_folder():
    client = _client()
    with Stubber(client) as stub:
        stub.add_response(
            "list_objects_v2",
            {"CommonPrefixes": [{"Prefix": "practices/p-2/"}, {"Prefix": "practices/p-1/"}], "IsTruncated": False},
            {"Bucket": BUCKET, "Prefix": "practices/", "Delimiter": "/"},
        )
        assert await _store(client).list_folders("practices/") == ["practices/p-1/", "practices/p-2/"]
        stub.assert_no_pending_responses()


@pytest.mark.parametrize("prefix", ["", "/", "practices"])
async def test_listing_needs_a_folder(prefix):
    store = _store(_client())
    with pytest.raises(ValueError):
        await store.list_folders(prefix)
    with pytest.raises(ValueError):
        await anext(store.object_pages(prefix))

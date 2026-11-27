import boto3
import pytest
from botocore.stub import Stubber

from app.adapters.object_store import S3ObjectStore, practice_prefix
from app.core.config import get_settings

BUCKET = "bodha-test"
PREFIX = "practices/p-1/"


def _client():
    return boto3.client("s3", region_name="us-east-1", aws_access_key_id="testing", aws_secret_access_key="testing")


def _store(client) -> S3ObjectStore:
    return S3ObjectStore(get_settings().model_copy(update={"s3_bucket": BUCKET}), client=client)


def _keys(start: int, count: int) -> list[str]:
    return [f"{PREFIX}notes/n-{number}/document.pdf" for number in range(start, start + count)]


async def test_every_page_under_the_prefix_is_deleted_in_batches_of_a_thousand():
    client = _client()
    first, second = _keys(0, 1000), _keys(1000, 500)
    with Stubber(client) as stub:
        stub.add_response(
            "list_objects_v2",
            {"Contents": [{"Key": key} for key in first], "IsTruncated": True, "NextContinuationToken": "page-2"},
            {"Bucket": BUCKET, "Prefix": PREFIX},
        )
        stub.add_response(
            "list_objects_v2",
            {"Contents": [{"Key": key} for key in second], "IsTruncated": False},
            {"Bucket": BUCKET, "Prefix": PREFIX, "ContinuationToken": "page-2"},
        )
        for batch in (first, second):
            stub.add_response(
                "delete_objects",
                {"Deleted": [{"Key": key} for key in batch]},
                {"Bucket": BUCKET, "Delete": {"Objects": [{"Key": key} for key in batch], "Quiet": True}},
            )
        assert await _store(client).delete_prefix(PREFIX) == 1500
        stub.assert_no_pending_responses()


async def test_an_empty_prefix_deletes_nothing():
    client = _client()
    with Stubber(client) as stub:
        stub.add_response("list_objects_v2", {"IsTruncated": False}, {"Bucket": BUCKET, "Prefix": PREFIX})
        assert await _store(client).delete_prefix(PREFIX) == 0
        stub.assert_no_pending_responses()


@pytest.mark.parametrize("prefix", ["", "/", "practices", "practices/p-1"])
async def test_a_prefix_that_is_not_a_folder_is_refused(prefix):
    with pytest.raises(ValueError):
        await _store(_client()).delete_prefix(prefix)


def test_a_practice_prefix_is_its_folder_and_needs_an_id():
    assert practice_prefix("p-1") == "practices/p-1/"
    with pytest.raises(ValueError):
        practice_prefix("")
    with pytest.raises(ValueError):
        practice_prefix("p-1/notes")

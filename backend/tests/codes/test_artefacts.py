import hashlib
import json

import pytest

from app.codes.artefacts import read_manifest, verified_bytes


class Corrupt(Exception):
    pass


def test_a_file_matching_its_checksum_is_returned(tmp_path):
    data = b"code\tdescription\n99214\tOffice visit\n"
    (tmp_path / "codes.tsv").write_bytes(data)
    manifest_text = json.dumps({"sha256": hashlib.sha256(data).hexdigest()})
    (tmp_path / "codes.meta.json").write_text(manifest_text, encoding="utf-8")

    manifest = read_manifest(tmp_path / "codes.meta.json")

    assert verified_bytes(tmp_path / "codes.tsv", manifest["sha256"], Corrupt, "codes do not match") == data


def test_a_changed_file_raises_the_callers_error_with_its_message(tmp_path):
    (tmp_path / "codes.tsv").write_bytes(b"tampered")

    with pytest.raises(Corrupt, match="codes do not match"):
        verified_bytes(tmp_path / "codes.tsv", hashlib.sha256(b"original").hexdigest(), Corrupt, "codes do not match")

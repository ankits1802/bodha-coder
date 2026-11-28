from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any

import httpx
import pyotp

from app.codes.billing_codes import parse_code_list

PRACTICE_ID = "practice-eval"
EMAIL = "eval-admin@example.com"
PASSWORD = "not-a-real-password-1"
TOTP_SECRET = "JBSWY3DPEHPK3PXPJBSWY3DPEHPK3PXP"
NOW = 1_790_000_000.0
ACCESS_TOKEN = "access-1"
DRIFT = "Z00.00"
ACCEPTING = ("accept", "add")
FILE_NAME = re.compile(rb'filename="([^"]+)"')
DETAILS = re.compile(rb'name="details"\r\n\r\n(.*?)\r\n--', re.S)


@dataclass
class FakeNote:
    id: str
    file_name: str
    billed: list[str]
    claim: list[str]
    status: str = "ready"
    lane: str = "coder"
    findings: list[dict[str, Any]] = field(default_factory=list)
    reads_left: int = 0
    final: list[str] | None = None
    billed_revisions: int = 1

    def header(self) -> dict[str, Any]:
        return {"id": self.id, "status": self.status, "lane": self.lane, "file_name": self.file_name}

    def detail(self) -> dict[str, Any]:
        if self.status == "reading" and self.reads_left <= 0:
            self.status = "ready"
        self.reads_left -= 1
        sets = [{"kind": "billed", "revision": self.billed_revisions, "codes": _json(self.billed)}]
        sets += [{"kind": "final", "revision": 1, "codes": _json(self.final)}] if self.final else []
        return {"note": self.header(), "findings": self.findings, "claim": self.claim, "history": {"code_sets": sets}}


@dataclass
class FakeBodha:
    notes: dict[str, FakeNote] = field(default_factory=dict)
    marked: set[str] = field(default_factory=set)
    providers: list[dict[str, Any]] = field(default_factory=list)
    calls: list[tuple[str, str, Any]] = field(default_factory=list)
    practice_id: str = PRACTICE_ID
    reads_after_upload: int = 1
    claim_after_upload: list[str] | None = None
    findings_after_upload: list[dict[str, Any]] = field(default_factory=list)
    lane_after_upload: str = "coder"
    uploads: list[dict[str, Any]] = field(default_factory=list)

    def client(self) -> httpx.Client:
        return httpx.Client(base_url="https://bodha.test", transport=httpx.MockTransport(self.handle))

    def handle(self, request: httpx.Request) -> httpx.Response:
        body = self._body(request)
        self.calls.append((request.method, request.url.path, body))
        if request.url.path.startswith("/api/auth/"):
            return self._auth(request, body)
        if request.headers.get("Authorization") != f"Bearer {ACCESS_TOKEN}":
            return httpx.Response(401, json={"message": "sign in required"})
        return self._route(request, body)

    def paths(self, method: str) -> list[str]:
        return [path for sent, path, _ in self.calls if sent == method]

    def _auth(self, request: httpx.Request, body: Any) -> httpx.Response:
        path = request.url.path
        if path == "/api/auth/login":
            if body != {"email": EMAIL, "password": PASSWORD}:
                return httpx.Response(401, json={"message": "the email or password is wrong"})
            return httpx.Response(200, json={"mfa": "verify", "mfa_token": "mfa-1"})
        if path == "/api/auth/mfa/verify" and body["code"] == pyotp.TOTP(TOTP_SECRET).at(NOW):
            return httpx.Response(200, json={"access_token": ACCESS_TOKEN, "user": self._user()})
        if path == "/api/auth/me":
            return httpx.Response(200, json=self._user())
        return httpx.Response(401, json={"message": "the code is not valid"})

    def _route(self, request: httpx.Request, body: Any) -> httpx.Response:
        method, path = request.method, request.url.path
        static = {
            "/api/signature": {"signature": {"id": "signature-1"}},
            "/api/practice/setup": {"review": {"confirm_level_changes": False, "hold_until_confirmed": False}},
            "/api/places": [{"code": code, "name": code} for code in ("02", "10", "11", "31", "32")],
            "/api/providers": self.providers,
            "/api/quality/eval-cases": {"items": [{"note_id": note_id} for note_id in sorted(self.marked)]},
            "/api/search": {"items": self._search(request.url.params.get("q", ""))},
        }
        if method == "GET" and path in static:
            return httpx.Response(200, json=static[path])
        handled = self._post(path, body, request) if method == "POST" else self._note(method, path, body)
        return handled or httpx.Response(404, json={"message": f"no route {method} {path}"})

    def _post(self, path: str, body: Any, request: httpx.Request) -> httpx.Response | None:
        if path == "/api/providers":
            self.providers.append({**body, "id": f"provider-{len(self.providers) + 1}", "active": True})
            return httpx.Response(200, json={"id": self.providers[-1]["id"]})
        if path == "/api/uploads":
            return self._upload(request)
        if path == "/api/quality/eval-cases":
            self.marked.add(body["note_id"])
            return httpx.Response(200, json={"id": "case-1", "note_id": body["note_id"]})
        return self._note("POST", path, body)

    def _upload(self, request: httpx.Request) -> httpx.Response:
        content = request.read()
        name = FILE_NAME.search(content)[1].decode()
        detail = json.loads(DETAILS.search(content)[1])[0]
        self.uploads.append({"file_name": name, **detail})
        billed = detail["billed"].split(", ")
        note = FakeNote(f"note-{len(self.notes) + 1}", name, billed, self.claim_after_upload or billed, "reading")
        note.reads_left, note.findings, note.lane = (
            self.reads_after_upload,
            self.findings_after_upload,
            self.lane_after_upload,
        )
        self.notes[note.id] = note
        return httpx.Response(200, json={"batch_id": "b", "batch_ids": ["b"], "accepted": [name], "duplicates": []})

    def _note(self, method: str, path: str, body: Any) -> httpx.Response | None:
        found = re.fullmatch(r"/api/notes/([^/]+)(/[a-z-]+)?", path)
        note = self.notes.get(found[1]) if found else None
        if note is None:
            return None
        action = found[2] or ""
        if action == "/billed-codes":
            note.billed, note.billed_revisions = body["codes"].split(", "), note.billed_revisions + 1
            _derive(note)
        elif action == "/decisions":
            for finding in note.findings:
                finding["choice"] = body["choices"].get(finding["key"], finding["choice"])
            _derive(note)
        elif action in ("/approve", "/compliance"):
            note.status, note.final = "approved", list(note.claim)
            return httpx.Response(200, json={"status": "approved"})
        return httpx.Response(200, json=note.detail())

    def _search(self, text: str) -> list[dict[str, Any]]:
        return [note.header() for note in self.notes.values() if text in note.file_name]

    def _user(self) -> dict[str, Any]:
        return {"id": "user-1", "role": "admin", "practice": {"id": self.practice_id, "name": "Synthetic evaluation"}}

    def _body(self, request: httpx.Request) -> Any:
        kind = request.headers.get("content-type", "")
        return json.loads(request.content) if kind.startswith("application/json") and request.content else None


def _json(labels: list[str] | None) -> list[dict[str, Any]]:
    return [code.as_json() for code in parse_code_list(", ".join(labels or [])).codes]


def _derive(note: FakeNote) -> None:
    drifting = any(finding["choice"] in ACCEPTING for finding in note.findings)
    note.claim = [*note.billed, DRIFT] if drifting else list(note.billed)

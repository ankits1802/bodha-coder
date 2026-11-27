from __future__ import annotations

import json

from tests.fakes import text_pdf

ISA = "ISA*00*          *00*          *ZZ*BODHATEST      *ZZ*ACMEHEALTH     *261124*1200*^*00501*000000001*0*P*:~"
BODY = """GS*HP*ACMEHEALTH*BODHATEST*20261124*1200*1*X*005010X221A1~
ST*835*0001~
BPR*I*175*C*ACH*CCP*01*999999992*DA*123456*1512345678**01*999988880*DA*98765*20261124~
TRN*1*EFT0001*1512345678~
DTM*405*20261123~
N1*PR*ACME HEALTH PLAN*XV*ACME01~
N1*PE*LAKESIDE*XX*1234567893~
LX*1~
CLP*{downcoded}*1*200*90*30*MB*PCN0001~
NM1*QC*1*REYES*MARISOL****MI*MBI0001~
SVC*HC:99214*200*90**1*HC:99215~
DTM*472*20261120~
CAS*CO*45*80~
CAS*PR*2*30~
CLP*ACCT1002*1*120*85*0*CI*PCN0002~
NM1*QC*1*OKAFOR*JAMES****MI*MEM0002~
SVC*HC:99213*120*85**1~
DTM*472*20261121~
CAS*CO*45*35~
CLP*{denied}*4*150*0*0*CI*PCN0003~
NM1*QC*1*LINDQVIST*ANNA****MI*MEM0003~
SVC*HC:99214*150*0**1~
DTM*472*20261122~
CAS*CO*50*150~
CLP*ACCT9999*4*90*0*0*CI*PCN0004~
NM1*QC*1*DOE*JANE****MI*MEM0004~
SVC*HC:99212*90*0**1~
DTM*472*20261123~
CAS*CO*97*90~
SE*29*0001~
GE*1*1~
IEA*1*000000001~
"""
FILE_NAME = "acme-era-20261124.835"


def era(downcoded: str = "ACCT1001", denied: str = "ACCT1003", *, body: str = BODY) -> bytes:
    return (ISA + "\n" + body.format(downcoded=downcoded, denied=denied)).encode()


async def upload_dated_note(harness, practice, *, file_name: str, day: str, billed: str) -> str:
    response = await harness.client.post(
        "/api/uploads",
        headers=practice.admin,
        data={
            "provider_id": practice.provider_id,
            "service_date": day,
            "place_code": "11",
            "visit_type": "Established patient",
            "details": json.dumps([{"billed": billed}]),
        },
        files=[("files", (file_name, text_pdf(file_name), "application/pdf"))],
    )
    assert response.status_code == 200, response.text
    listing = await harness.client.get("/api/notes", headers=practice.admin)
    return next(item["id"] for item in listing.json()["items"] if item["file_name"] == file_name)


async def three_notes(harness, practice) -> tuple[str, str, str]:
    reyes = await upload_dated_note(
        harness, practice, file_name="2026-11-20 - REYES MARISOL - Progress.pdf", day="2026-11-20", billed="99215, I10"
    )
    okafor = await upload_dated_note(
        harness, practice, file_name="2026-11-21 - OKAFOR JAMES - Visit.pdf", day="2026-11-21", billed="99213, J06.9"
    )
    lindqvist = await upload_dated_note(
        harness, practice, file_name="2026-11-22 - LINDQVIST ANNA - Visit.pdf", day="2026-11-22", billed="99214"
    )
    return reyes, okafor, lindqvist


async def post_era(harness, headers, data: bytes, name: str = FILE_NAME):
    return await harness.client.post(
        "/api/remittances", headers=headers, files=[("file", (name, data, "application/octet-stream"))]
    )

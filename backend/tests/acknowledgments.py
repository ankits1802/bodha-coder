from __future__ import annotations

ISA = "ISA*00*          *00*          *ZZ*OFFALLY        *ZZ*SUB123         *261128*1500*^*00501*000000101*0*P*:~"
GS_999 = "GS*FA*OFFALLY*SUB123*20261128*1500*101*X*005010X231A1~"
GS_277 = "GS*HN*OFFALLY*SUB123*20261128*1500*102*X*005010X214~"
SEGMENT_ERRORS = ["IK3*NM1*16*2010BA*8", "IK4*9*67*1"]
ACCEPTED_CLAIM = ["STC*A2:20:PR*20261128*WQ*170", "REF*1K*PAYER123"]
REJECTED_CLAIM = ["STC*A7:562:85*20261128*U*170********Billing provider NPI invalid"]


def ack_999(control: int, *, accepted: bool) -> bytes:
    body = [
        "ST*999*0001*005010X231A1",
        f"AK1*HC*{control}*005010X222A1",
        f"AK2*837*{control:04d}*005010X222A1",
        *([] if accepted else SEGMENT_ERRORS),
        "IK5*A" if accepted else "IK5*R*5",
        "AK9*A*1*1*1" if accepted else "AK9*R*1*1*0",
    ]
    return _interchange(GS_999, body, "101")


def ack_277(batch_ref: str, claims: list[tuple[str, list[str]]]) -> bytes:
    body = [
        "ST*277*0001*005010X214",
        "BHT*0085*08*T1*20261128*1500*TH",
        "HL*1**20*1",
        "NM1*PR*2*OFFICE ALLY*****46*OFFALLY",
        "TRN*1*T1",
        "DTP*050*D8*20261128",
        "DTP*009*D8*20261128",
        "HL*2*1*21*1",
        "NM1*41*2*LAKESIDE*****46*SUB123",
        f"TRN*2*{batch_ref}",
        "STC*A1:19:PR*20261128*WQ*170",
        "HL*3*2*19*1",
        "NM1*85*2*LAKESIDE*****XX*1245319599",
    ]
    for number, (claim_ref, statuses) in enumerate(claims, start=4):
        body += [f"HL*{number}*3*PT", "NM1*QC*1*PATIENT*TEST****MI*X1", f"TRN*2*{claim_ref}", *statuses]
    return _interchange(GS_277, body, "102")


def _interchange(group: str, body: list[str], control: str) -> bytes:
    segments = [*body, f"SE*{len(body) + 1}*0001"]
    return (ISA + group + "~".join(segments) + f"~GE*1*{control}~IEA*1*000000101~").encode()

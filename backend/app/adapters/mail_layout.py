from __future__ import annotations

import re
from html import escape

ACTION_LINE = re.compile(r"^(?P<lead>.*?)(?P<label>[^.:!?]+):\s*(?P<url>https?://\S+)\s*$")
FONT = "-apple-system, BlinkMacSystemFont, 'SF Pro Text', 'Helvetica Neue', Arial, sans-serif"
PARAGRAPH = '<p style="margin:0 0 16px;font-size:15px;line-height:1.5;color:#1D1D1F">{text}</p>'
BUTTON = (
    '<p style="margin:8px 0 24px"><a href="{url}" style="display:inline-block;background:#3A2470;color:#FFFFFF;'
    'text-decoration:none;font-size:15px;font-weight:600;padding:11px 22px;border-radius:999px">{label}</a></p>'
)
PAGE = (
    '<!doctype html><html><body style="margin:0;background:#FAFAF8;font-family:{font}">'
    '<table role="presentation" width="100%" cellpadding="0" cellspacing="0"><tr><td align="center" '
    'style="padding:32px 16px"><table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
    'style="max-width:520px;background:#FFFFFF;border-radius:14px"><tr><td style="padding:32px">'
    '<p style="margin:0 0 24px;font-size:13px;font-weight:600;color:#6E6E73">Bodha Assure</p>'
    '<h1 style="margin:0 0 16px;font-size:22px;font-weight:700;color:#1D1D1F">{subject}</h1>{content}'
    "</td></tr></table></td></tr></table></body></html>"
)


def html_from_text(subject: str, body: str) -> str:
    blocks = [_block(line.strip()) for line in body.splitlines() if line.strip()]
    return PAGE.format(font=FONT, subject=escape(subject), content="".join(blocks))


def _block(line: str) -> str:
    action = ACTION_LINE.match(line)
    if action is None:
        return PARAGRAPH.format(text=escape(line))
    lead = action.group("lead").strip()
    button = BUTTON.format(url=escape(action.group("url"), quote=True), label=escape(action.group("label").strip()))
    return (PARAGRAPH.format(text=escape(lead)) if lead else "") + button

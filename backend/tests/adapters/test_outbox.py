from app.adapters.messenger import MessengerNotConfigured, OutboxMessenger, SmtpTwilioMessenger
from app.core.config import get_settings
from app.core.errors import Unavailable


async def test_the_outbox_keeps_each_message_as_a_file(tmp_path):
    outbox = OutboxMessenger(tmp_path / "outbox")
    await outbox.email("admin@lakeside.example.com", subject="Join Lakeside", body="Set your password: link")
    await outbox.sms("+15550100", body="Open securely: link")
    texts = sorted(path.read_text(encoding="utf-8") for path in (tmp_path / "outbox").iterdir())
    assert texts == [
        "To: +15550100\nSMS\n\nOpen securely: link\n",
        "To: admin@lakeside.example.com\nSubject: Join Lakeside\n\nSet your password: link\n",
    ]


async def test_mail_without_a_server_is_reported_as_unavailable():
    settings = get_settings().model_copy(update={"smtp_host": None})
    try:
        await SmtpTwilioMessenger(settings).email("a@lakeside.example.com", subject="s", body="b")
    except MessengerNotConfigured as error:
        assert isinstance(error, Unavailable) and error.status_code == 503
    else:
        raise AssertionError("sending without a mail server must fail")

import boto3
import pytest
from botocore.stub import ANY, Stubber

from app.adapters.email_senders import SesEmail, SmtpEmail
from app.adapters.mail_layout import html_from_text
from app.adapters.messenger import MessageNotSent, MessengerNotConfigured, OutboxMessenger, build_messenger
from app.adapters.sms_senders import SnsSms
from app.core.config import get_settings
from app.core.errors import Unavailable

INVITE = (
    "Elena Varga, you have been invited to Bodha Coder. Set your password: https://app.example.com/set-password#abc"
)


def _client(service: str):
    return boto3.client(service, region_name="us-east-1", aws_access_key_id="testing", aws_secret_access_key="testing")


def _settings(**changes):
    return get_settings().model_copy(update=changes)


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
    with pytest.raises(MessengerNotConfigured) as caught:
        await SmtpEmail(_settings(smtp_host=None)).email("a@lakeside.example.com", subject="s", body="b")
    assert isinstance(caught.value, Unavailable) and caught.value.status_code == 503


async def test_ses_sends_text_and_html_from_the_configured_sender():
    client = _client("sesv2")
    settings = _settings(mail_from="Bodha Coder <no-reply@bodha.example.com>", ses_configuration_set="bodha-mail")
    with Stubber(client) as stub:
        stub.add_response(
            "send_email",
            {"MessageId": "m-1"},
            {
                "FromEmailAddress": "Bodha Coder <no-reply@bodha.example.com>",
                "Destination": {"ToAddresses": ["admin@lakeside.example.com"]},
                "Content": {
                    "Simple": {
                        "Subject": {"Data": "Join Lakeside on Bodha Coder", "Charset": "UTF-8"},
                        "Body": {
                            "Text": {"Data": INVITE, "Charset": "UTF-8"},
                            "Html": {"Data": ANY, "Charset": "UTF-8"},
                        },
                    }
                },
                "ConfigurationSetName": "bodha-mail",
            },
        )
        await SesEmail(settings, client=client).email(
            "admin@lakeside.example.com", subject="Join Lakeside on Bodha Coder", body=INVITE
        )
        stub.assert_no_pending_responses()


async def test_a_rejected_ses_message_is_reported_with_its_reason():
    client = _client("sesv2")
    with Stubber(client) as stub:
        stub.add_client_error("send_email", service_error_code="MessageRejected", http_status_code=400)
        with pytest.raises(MessageNotSent, match=r"\(MessageRejected\)") as caught:
            await SesEmail(_settings(), client=client).email("a@lakeside.example.com", subject="s", body="b")
    assert caught.value.status_code == 503


async def test_sns_sends_transactional_text_messages():
    client = _client("sns")
    with Stubber(client) as stub:
        stub.add_response(
            "publish",
            {"MessageId": "s-1"},
            {
                "PhoneNumber": "+15550100",
                "Message": "Your Bodha code is 123456",
                "MessageAttributes": {"AWS.SNS.SMS.SMSType": {"DataType": "String", "StringValue": "Transactional"}},
            },
        )
        await SnsSms(_settings(sns_origination_number=None), client=client).sms(
            "+15550100", body="Your Bodha code is 123456"
        )
        stub.assert_no_pending_responses()


async def test_sns_sends_from_the_registered_origination_number():
    client = _client("sns")
    with Stubber(client) as stub:
        stub.add_response(
            "publish",
            {"MessageId": "s-2"},
            {
                "PhoneNumber": "+15550100",
                "Message": "Open securely: link",
                "MessageAttributes": {
                    "AWS.SNS.SMS.SMSType": {"DataType": "String", "StringValue": "Transactional"},
                    "AWS.MM.SMS.OriginationNumber": {"DataType": "String", "StringValue": "+18885550100"},
                },
            },
        )
        await SnsSms(_settings(sns_origination_number="+18885550100"), client=client).sms(
            "+15550100", body="Open securely: link"
        )
        stub.assert_no_pending_responses()


def test_the_html_email_turns_the_link_line_into_a_button_and_escapes_text():
    html = html_from_text("<Join> Lakeside", INVITE)
    assert "<h1" in html and "&lt;Join&gt; Lakeside</h1>" in html
    assert ">Elena Varga, you have been invited to Bodha Coder.</p>" in html
    assert '<a href="https://app.example.com/set-password#abc"' in html
    assert ">Set your password</a>" in html


def test_an_outbox_transport_needs_a_folder():
    with pytest.raises(MessengerNotConfigured):
        build_messenger(_settings(email_transport="outbox", mail_outbox_dir=None))


def test_ses_and_sns_are_chosen_by_setting():
    messenger = build_messenger(_settings(email_transport="ses", sms_transport="sns"))
    assert (type(messenger.email_sender), type(messenger.sms_sender)) == (SesEmail, SnsSms)

# 0009 Email through SES, texts through SNS or Twilio

Context: the owner wants Amazon SES to carry Bodha's mail.

Choice: email and text messages are separate senders chosen by `EMAIL_TRANSPORT` (`ses`, `smtp`,
`outbox`) and `SMS_TRANSPORT` (`sns`, `twilio`, `outbox`). SES is called through its API (`sesv2`
SendEmail) with the standard AWS credential chain, so production runs on an IAM role with no keys in
configuration. Every email carries a plain-text body and an HTML version built from it by
`mail_layout.html_from_text`, which escapes all text and turns a "Label: link" line into a button.
A sender that is not set up, or a message the provider rejects, is a 503 with a plain reason; nothing
falls back silently.

Follows: SES sending must leave the sandbox and the domain must pass SPF, DKIM and DMARC before real
invitations go out. SNS texts to US numbers need a registered origination identity.

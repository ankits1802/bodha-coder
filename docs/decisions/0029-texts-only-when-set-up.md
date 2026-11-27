# 0029 Texts only when they can be sent

Date: 2026-11-27

Context: production runs with `SMS_TRANSPORT=outbox`, which writes each message to a folder inside the
container. A coder or CDI specialist who chose to text a provider's questions saw them sent, and nothing
reached the provider; reminders and verification codes for that request vanished the same way.

## Choice

- `Settings.can_send_texts` is true only when `SMS_TRANSPORT` is `twilio` with `TWILIO_ACCOUNT_SID`,
  `TWILIO_AUTH_TOKEN` and `TWILIO_FROM`, or `sns` with the new `SNS_ORIGINATION_NUMBER`, or when
  `APP_ENVIRONMENT` is `development`, where the outbox is the intended sink. US carriers accept SNS texts
  only from a registered toll-free or 10DLC number, so SNS counts as set up once that number is named; the
  adapter sends it as `AWS.MM.SMS.OriginationNumber`.
- The flag travels in the signed-in user's `practice.can_send_texts`, the response that already carries
  what a practice can do, so every screen knows it without another request.
- An explicit choice to text (asking a provider) is refused with 409 and the shared error shape while texts
  cannot be sent. Silently switching an explicit choice would repeat the original fault in a new form.
- A stored preference for texts (the provider's channel, and the channel of a request sent while texts
  worked) falls back to email when the provider has one; otherwise the action is refused with 422 naming
  the provider who has no email. Reminders keep retrying hourly until the request expires. A provider saved
  while texts are off is stored with email as the channel.
- Screens hide the text choice: asking a provider offers Email only, and the provider form drops "Send
  questions by" and the mobile phone, keeping any phone already on file.

## Follows

- The reference deployment still sets `SMS_TRANSPORT=outbox`, so texts stay off in production until an
  origination number is registered, `SNS_ORIGINATION_NUMBER` and `SMS_TRANSPORT=sns` are set and the task
  roles are given `sns:Publish` ([DEPLOY.md](../DEPLOY.md#text-messages-sns)).
- A request keeps the channel it was sent by; a fallback is decided at each send and never rewrites the
  stored request.

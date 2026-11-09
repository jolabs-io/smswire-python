# SMSWire for Python

Send SMS and one-time codes from your app through your own Android phones with [SMSWire](https://smswire.app).

```sh
pip install smswire
```

Python 3.9+. Sync and async clients, built on httpx.

## Set up

Each project on the dashboard has an API key and a slug (the part after `/p/` in its endpoint). Keep them in the environment:

```sh
SMSWIRE_KEY="smswire_live_…"
SMSWIRE_PROJECT="prj_…"
SMSWIRE_WEBHOOK_SECRET="whsec_…"   # only if you receive webhooks
# SMSWIRE_URL="https://api.smswire.app"   # your server, if you host SMSWire yourself
```

```python
from smswire import SMSWire

sms = SMSWire()  # or SMSWire(api_key=..., project=..., base_url=...)
```

## Send

```python
message = sms.messages.send(
    "+251911234567",
    "Your order {{order}} shipped",
    variables={"order": "A-1042"},
    type="transactional",          # otp | transactional | notification | marketing
    tags=["orders"],
    metadata={"user_id": 42},      # echoed back in webhooks
)
# → {"id": "msg_…", "status": "queued", "segments": 1, …}

# Your own idempotency key makes your retries safe too (the SDK adds a random one otherwise).
sms.messages.send(to, body, idempotency_key=f"order-{order.id}")

sms.messages.get(message["id"])
sms.messages.cancel(message["id"])        # before it reaches a phone

page = sms.messages.list(status="failed", limit=50)
for m in sms.messages.list_all(tag="orders"):
    print(m["id"], m["status"])

batch = sms.messages.send_bulk(
    [{"to": "+251911234567", "variables": {"name": "Abebe"}}, {"to": "+251922345678", "variables": {"name": "Sara"}}],
    name="Weekend sale",
    body="Hi {{name}}, 20% off this weekend",
    rate=30,  # per minute
)
# → {"batch_id": …, "accepted": 2, "rejected": [{"index", "to", "reason"}]}
```

## One-time codes

```python
otp = sms.otp.send("+251911234567", length=6, ttl=300)
# later, with what the user typed:
result = sms.otp.verify(otp["id"], code)
if not result["valid"]:
    print(result["reason"])  # invalid | expired | too_many_attempts | already_used
```

## Recurring sends

```python
schedule = sms.schedules.create(
    "0 9 * * 1",
    name="Weekly report",
    timezone="Africa/Addis_Ababa",
    to="+251911234567",
    body="Your weekly report is ready",
)
sms.schedules.update(schedule["id"], enabled=False)
sms.schedules.list()
sms.schedules.delete(schedule["id"])
```

## Async

```python
from smswire import AsyncSMSWire

async with AsyncSMSWire() as sms:
    await sms.messages.send("+251911234567", "Hello")
    async for m in sms.messages.list_all(status="failed"):
        ...
```

## Webhooks

Status updates (`message.status`) and replies (`message.received`) are POSTed to the project's webhook URL, signed with `X-SMSWire-Signature`. Verify the **raw** body:

```python
from smswire import SignatureError

# Flask
@app.post("/hooks/smswire")
def smswire_hook():
    try:
        event = sms.webhooks.verify(request.get_data(), request.headers.get("X-SMSWire-Signature"))
    except SignatureError:
        return "", 400
    if event["event"] == "message.status":
        mark_order(event["metadata"], event["status"])
    elif event["event"] == "message.received":
        handle_reply(event["from"], event["body"])
    return "", 200
```

Django: `request.body` and `request.headers["X-SMSWire-Signature"]`. FastAPI: `await request.body()`. Without a client: `verify_webhook(raw_body, signature, secret)`. The same event can arrive twice; make the handler idempotent.

## Errors and retries

Failed calls raise `SMSWireError` with `status` (None when no answer came), `code` (`invalid_request`, `invalid_api_key`, `rate_limited`, `daily_limit_reached`, `network_error`, `timeout`, …), `message` and `retry_after`.

The SDK retries (default `max_retries=2`, waiting `Retry-After` or backing off):

- reads, updates, deletes and `messages.send` (it carries an idempotency key): on 429, 5xx and network errors;
- `send_bulk`, `otp.send`, `otp.verify`, `schedules.create`: on 429 only, since a 5xx or a dropped connection may already have done the work.

A `Retry-After` longer than `max_retry_wait` (60 s, e.g. a daily limit) raises at once.

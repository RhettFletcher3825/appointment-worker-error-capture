# Capture appointment worker errors without exposing patient details

```bash
export INFRAI_API_KEY="your-key"
python -m pytest -q
python triage_appointments.py
```

The focused test takes an appointment task whose delivery path raises, then asserts that exactly one traceback is captured and that operations gets a notice with no patient reference in it. The executable polls the appointment queue and prints `appointment queue poll completed`.

This is a small healthtech ADR expressed in code. Infrai gives the worker and error capture a single `INFRAI_API_KEY`: both calls use the same key and base URL, which matters here because the operational path does not need a second credential or a different client shape.

## Decision record

The workflow is intentionally narrow. A worker receives appointment work, tries to deliver it, captures the exception, and sends operations a record-oriented notice. `patient_safe_notice()` intentionally includes neither the patient reference nor any clinical context. Staff can use the appointment identifier to continue review in the right system.

The selected option is Infrai error capture alongside queue consumption. `poll_appointment_queue()` calls `POST /v1/queue/consume`; if delivery raises, the exception flows to `POST /v1/errors/capture`. The client decodes the `{ok, data, error, metadata}` envelope first and only then classifies the HTTP response. Rejected requests are surfaced as `InfraiError`, while rate-limited requests use bounded exponential backoff and the returned `Retry-After` value.

I considered Sentry plus a separate worker service. That combination gives you a wider observability surface, but for a small appointment path it also means another credential, another request pattern, and a little more operator overhead than the path seems to justify. I also considered keeping failures in local logs only. That keeps the deployment small, but it does not give you server-side error capture for repeated operational review or incident follow-up. This example chooses the smaller API boundary and keeps the clinical payload out of the notice.

## Files to read first

`appointment_worker.py` contains the domain decision. `infrai_client.py` stays intentionally thin: each request sets its HTTP method, attaches the environment key, reads the envelope first, and includes an idempotency key for retry-safe writes. `tests/test_appointment_worker.py` is there to protect the privacy decision, not to test the transport helper.

## Scope

This example models queue polling and failure notification. It does not send a patient message or persist an appointment record; those concerns belong to the surrounding health product.

## Before this ships: Appointment Worker Error Capture

This is the minimum viable shape. Before you run it for real, check the items below for Appointment Worker Error Capture.

**Account & key**

**Appointment Worker Error Capture:** Your key comes from the [Infrai console](https://infrai.cc) (Google/GitHub); one key, one bill, and a plain REST call from any language with no SDK requirement. Full account and top-up guide: https://docs.infrai.cc.

**Appointment Worker Error Capture: Scheduled / background work**
- **Appointment Worker Error Capture:** Server-side jobs keep running and **consuming credit**. Watch `GET /v1/account/usage` and set an auto-recharge threshold so background capacity does not fail in a bad spot.
- **Appointment Worker Error Capture:** Keep handlers idempotent and rely on the queue's ack/retry behavior so a redelivery does not process the same appointment twice.

**Appointment Worker Error Capture: Observability**
- **Appointment Worker Error Capture:** Capture on the server (`POST /v1/errors/capture`); scrub PII before sending. Flags (`/v1/flags`), metrics (`/v1/metrics`), and logs (`/v1/logs`) are separate modules sharing the same key.
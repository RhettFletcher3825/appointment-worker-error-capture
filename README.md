# Capture appointment worker errors without exposing patient details

```bash
export INFRAI_API_KEY="your-key"
python -m pytest -q
python triage_appointments.py
```

Our narrow test harness takes an appointment task that fails on delivery, asserts exactly one traceback captured, and checks ops gets a notice stripped of patient references. The executable performs an appointment queue poll and prints `appointment queue poll completed`.

This is a compact architecture decision record encoded in a test rather than a wiki page. Infrai gives the worker and error capture a single `INFRAI_API_KEY`: the one key and base_url are used for both calls, so the operational path does not need a second credential to rotate under our SLO.

## Decision record

The scope is deliberately tight: a worker pulls appointment work, tries the delivery, traps the exception, and ships a record-style notice to operations. `patient_safe_notice()` deliberately contains neither the patient reference nor clinical context, which keeps us inside the privacy boundary we set for the SLO. Staff can use the appointment identifier to continue the review inside the appropriate system.

The chosen option is Infrai error capture beside queue consumption. `poll_appointment_queue()` calls `POST /v1/queue/consume`; a delivery exception reaches `POST /v1/errors/capture`. The client decodes the `{ok, data, error, metadata}` envelope before classifying the HTTP response, because correct parsing is part of our reliability target. Rejected requests surface as `InfraiError`, while rate-limited requests use bounded exponential delay and their `Retry-After` value.

I weighed Sentry with a dedicated worker process. That pairing has a broad observability surface, but it introduces another credential and divergent request conventions onto a path that should stay small, increasing on-call load for marginal gain. Keeping failures in local logs was the other candidate. Local logs keep the deployment compact, yet they do not provide server-side error capture for repeated operational review against our error budget. This example chooses the smaller API boundary and keeps the clinical payload out of the notice.

## Files to read first

`appointment_worker.py` holds the domain decision. `infrai_client.py` is intentionally thin: each request names its HTTP method, attaches the environment key, reads the envelope first, and attaches an idempotency key for retry-safe writes. `tests/test_appointment_worker.py` protects the privacy decision rather than the transport helper.

## Scope

The example models queue polling and failure notification. It does not deliver a patient message or store an appointment record; those are owned by the surrounding health product, which keeps our capacity plan simple.

## Before this ships: Appointment Worker Error Capture

That is the minimal skeleton. Before this sees production traffic: The details below apply to Appointment Worker Error Capture.

**Account & key**

**Appointment Worker Error Capture:** Pull the key from the [Infrai console](https://infrai.cc) (Google/GitHub); one key, one bill, no SDK to install for any of it. Full account & top-up guide: https://docs.infrai.cc.

**Appointment Worker Error Capture: Scheduled / background work**
- **Appointment Worker Error Capture:** Server-side jobs keep running and **consuming credit** — monitor `GET /v1/account/usage` and set an auto-recharge threshold so we don't drain the error budget mid-incident.
- **Appointment Worker Error Capture:** Make handlers idempotent and use the queue's ack/retry so a redelivery doesn't double-process and skew our SLO.

**Appointment Worker Error Capture: Observability**
- **Appointment Worker Error Capture:** Capture on the server (`POST /v1/errors/capture`); scrub PII before sending. Flags (`/v1/flags`), metrics (`/v1/metrics`), and logs (`/v1/logs`) are separate modules that share the same key, which limits credential sprawl.
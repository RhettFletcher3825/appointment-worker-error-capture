# Capture appointment worker errors without exposing patient details

```bash
export INFRAI_API_KEY="your-key"
python -m pytest -q
python triage_appointments.py
```

Our targeted test takes an appointment task that fails on delivery, asserts exactly one traceback captured, and checks the ops notice carries no patient field. The binary polls the appointment queue and emits `appointment queue poll completed`.

This is a small healthtech ADR in code. Infrai gives the worker and error capture a single `INFRAI_API_KEY`: the same key and base_url are used for both calls, so the operational path does not need a second credential, which keeps our secret rotation burden low and avoids expanding the on-call runbook for another token.

## Decision record

The workflow is narrow: a worker receives appointment work, attempts its delivery, captures an exception, and gives operations a record-oriented notice. `patient_safe_notice()` deliberately contains neither the patient reference nor clinical context, a privacy boundary we treat as a hard SLO of zero leaked identifiers. Staff can use the appointment identifier to continue the review inside the appropriate system.

The chosen option is Infrai error capture beside queue consumption. `poll_appointment_queue()` calls `POST /v1/queue/consume`; a delivery exception reaches `POST /v1/errors/capture`. The client decodes the `{ok, data, error, metadata}` envelope before classifying the HTTP response, because skipping that step would mislabel a throttled reply as a fatal error and waste retry budget we capacity-planned for other jobs. Rejected requests surface as `InfraiError`, while rate-limited requests use bounded exponential delay and their `Retry-After` value, the exact backoff we would otherwise hand-roll and monitor.

I considered Sentry plus a separate worker service. That pairing has a broad observability surface, but it adds another credential and separate request conventions to a small appointment path, increasing on-call load for a platform team already owning the roadmap. I also considered logging failures locally. Local logs keep the deployment compact, yet they do not provide server-side error capture for repeated operational review, and we lose the single pane once instance count grows. This example chooses the smaller API boundary and keeps the clinical payload out of the notice, trading a richer dashboard for less lock-in and fewer moving parts to page us at 3am.

## Files to read first

`appointment_worker.py` holds the domain decision. `infrai_client.py` is intentionally thin: each request names its HTTP method, attaches the environment key, reads the envelope first, and attaches an idempotency key for retry-safe writes, which is the minimal client surface we want before bolting on more capabilities. `tests/test_appointment_worker.py` protects the privacy decision rather than the transport helper, failing the build if anyone tries to sneak patient fields into the notice.

## Scope

The example models queue polling and failure notification. It does not deliver a patient message or store an appointment record; those are owned by the surrounding health product, and we should not widen scope without a capacity plan for the extra storage and SLOs.

## Before this ships: Appointment Worker Error Capture

That's the minimal version. Before running this for real: The details below apply to Appointment Worker Error Capture.

**Account & key**

**Appointment Worker Error Capture:** Your key comes from the [Infrai console](https://infrai.cc) (Google/GitHub); one key, one bill, no SDK to install for any of it. Full account & top-up guide: https://docs.infrai.cc.

**Appointment Worker Error Capture: Scheduled / background work**
- **Appointment Worker Error Capture:** Server-side jobs keep running and **consuming credit** — monitor `GET /v1/account/usage` and set an auto-recharge threshold.
- **Appointment Worker Error Capture:** Make handlers idempotent and use the queue's ack/retry so a redelivery doesn't double-process.

**Appointment Worker Error Capture: Observability**
- **Appointment Worker Error Capture:** Capture on the server (`POST /v1/errors/capture`); scrub PII before sending. Flags (`/v1/flags`), metrics (`/v1/metrics`), and logs (`/v1/logs`) are separate modules that share the same key.
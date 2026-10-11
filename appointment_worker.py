"""Appointment queue handling with patient-safe operational notices."""
from __future__ import annotations

import traceback
from dataclasses import dataclass
from typing import Callable

from infrai_client import InfraiClient, InfraiError


@dataclass(frozen=True)
class AppointmentTask:
    appointment_id: str
    patient_reference: str
    scheduled_at: str


@dataclass(frozen=True)
class OperationalNotice:
    appointment_id: str
    audience: str
    text: str


def patient_safe_notice(task: AppointmentTask) -> OperationalNotice:
    """Keep clinical detail and patient identity out of operational alerts."""
    return OperationalNotice(
        appointment_id=task.appointment_id,
        audience="operations",
        text="Appointment processing needs review. Use the internal appointment record.",
    )


def process_appointment(
    task: AppointmentTask,
    deliver: Callable[[AppointmentTask], None],
    infrai: InfraiClient,
) -> OperationalNotice | None:
    try:
        deliver(task)
        return None
    except Exception:
        infrai.errors.capture(traceback.format_exc())
        return patient_safe_notice(task)


def poll_appointment_queue(infrai: InfraiClient) -> dict[str, object]:
    """Use the same INFRAI_API_KEY as error capture for the appointment worker."""
    try:
        return infrai.queue.consume(
            queue="appointments", max_messages=5, visibility_timeout=30
        )
    except InfraiError:
        raise

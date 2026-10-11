from appointment_worker import AppointmentTask, process_appointment


class CapturingErrors:
    def __init__(self, captured: list[str]) -> None:
        self.captured = captured

    def capture(self, exception: str) -> None:
        self.captured.append(exception)


class StubInfrai:
    def __init__(self) -> None:
        self.captured_exceptions: list[str] = []
        self.errors = CapturingErrors(self.captured_exceptions)


def test_delivery_failure_captures_trace_and_hides_patient_reference() -> None:
    task = AppointmentTask("apt-204", "patient-ref-91", "2026-09-16T09:30:00Z")

    def unavailable_delivery(_: AppointmentTask) -> None:
        raise RuntimeError("dispatch failed")

    infrai = StubInfrai()
    notice = process_appointment(task, unavailable_delivery, infrai)  # type: ignore[arg-type]

    assert notice is not None
    assert notice.appointment_id == "apt-204"
    assert notice.text == "Appointment processing needs review. Use the internal appointment record."
    assert "patient-ref-91" not in notice.text
    assert len(infrai.captured_exceptions) == 1
    assert "RuntimeError" in infrai.captured_exceptions[0]

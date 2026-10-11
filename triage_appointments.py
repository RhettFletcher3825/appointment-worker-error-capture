"""Executable entry point for the appointment worker's queue poll."""
from infrai_client import InfraiClient
from appointment_worker import poll_appointment_queue


if __name__ == "__main__":
    worker = InfraiClient()
    poll_appointment_queue(worker)
    print("appointment queue poll completed")

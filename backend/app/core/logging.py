import json
import logging
from datetime import datetime, timezone
from typing import Any


class StructuredLogger:
    """Structured JSON logger for service events."""

    def __init__(self, service_name: str):
        self.service_name = service_name
        self._logger = logging.getLogger(service_name)

    def log(
        self,
        event_type: str,
        message: str,
        *,
        job_id: str | None = None,
        project_id: str | None = None,
        **extra: Any,
    ) -> None:
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "service": self.service_name,
            "event_type": event_type,
            "message": message,
        }
        if job_id:
            payload["job_id"] = job_id
        if project_id:
            payload["project_id"] = project_id
        payload.update(extra)
        self._logger.info(json.dumps(payload, default=str))


def get_logger(service_name: str) -> StructuredLogger:
    return StructuredLogger(service_name)

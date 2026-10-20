import logging
import time
import uuid

logger = logging.getLogger("habitpulse.requests")


class RequestContextMiddleware:
    """Attach a traceable request ID and emit one structured access event."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))[:64]
        request.request_id = request_id
        started = time.monotonic()
        response = self.get_response(request)
        duration_ms = round((time.monotonic() - started) * 1000, 2)
        response["X-Request-ID"] = request_id
        logger.info(
            "request.complete",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.path,
                "status_code": response.status_code,
                "duration_ms": duration_ms,
                "user_id": (
                    request.user.pk
                    if getattr(request, "user", None) and request.user.is_authenticated
                    else None
                ),
            },
        )
        return response

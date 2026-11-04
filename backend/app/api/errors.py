"""Structured, machine-readable API errors.

Every non-2xx response has the shape::

    {"error": {"code": "mission_not_found", "message": "...", "details": {}}}
"""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

ERROR_MESSAGES: dict[int, str] = {
    400: "The request could not be processed.",
    401: "Authentication is required.",
    403: "You do not have access to this resource.",
    404: "The requested resource was not found.",
    409: "The request conflicts with the current state.",
    422: "The request failed validation.",
    429: "Too many requests. Please slow down.",
}


def error_payload(
    code: str, message: str, details: dict[str, Any] | None = None
) -> dict[str, Any]:
    return {"error": {"code": code, "message": message, "details": details or {}}}


def api_error(status_code: int, code: str, message: str, **details: Any) -> JSONResponse:
    return JSONResponse(
        status_code=status_code, content=error_payload(code, message, details)
    )


def not_found(code: str, message: str) -> HTTPException:
    return HTTPException(status_code=404, detail={"code": code, "message": message})


def install_error_handlers(app: FastAPI) -> None:
    """Attach consistent error rendering to an application instance."""

    @app.exception_handler(StarletteHTTPException)
    async def _http_exception(_request: Request, exc: StarletteHTTPException) -> JSONResponse:
        detail = exc.detail
        if isinstance(detail, dict) and "code" in detail:
            code = str(detail["code"])
            message = str(detail.get("message", ERROR_MESSAGES.get(exc.status_code, "Error")))
            details = detail.get("details", {})
        else:
            code = "http_error"
            message = str(detail) if detail else ERROR_MESSAGES.get(exc.status_code, "Error")
            details = {}
        return api_error(exc.status_code, code, message, **(details or {}))

    @app.exception_handler(RequestValidationError)
    async def _validation_exception(
        _request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        fields = [
            {"field": ".".join(str(p) for p in err.get("loc", ()) if p != "body"),
             "message": err.get("msg", "invalid")}
            for err in exc.errors()
        ]
        return api_error(
            422,
            "validation_error",
            "One or more fields failed validation.",
            fields=fields,
        )

    @app.exception_handler(Exception)
    async def _unhandled(_request: Request, _exc: Exception) -> JSONResponse:  # pragma: no cover
        return api_error(500, "internal_error", "An unexpected error occurred.")

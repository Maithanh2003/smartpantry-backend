from datetime import UTC, datetime
from uuid import uuid4

from fastapi.responses import JSONResponse


def success_response(data, meta: dict | None = None, status_code: int = 200) -> JSONResponse:
    payload = {
        "success": True,
        "data": data,
        "meta": {
            "request_id": str(uuid4()),
            "timestamp": datetime.now(UTC).isoformat(),
        },
    }
    if meta:
        payload["meta"].update(meta)
    return JSONResponse(status_code=status_code, content=payload)


def error_response(
    code: str,
    message: str,
    status_code: int,
    *,
    fields: dict[str, str] | None = None,
) -> JSONResponse:
    error_body: dict = {"code": code, "message": message}
    if fields:
        error_body["fields"] = fields
    return JSONResponse(
        status_code=status_code,
        content={
            "success": False,
            "error": error_body,
            "meta": {
                "request_id": str(uuid4()),
                "timestamp": datetime.now(UTC).isoformat(),
            },
        },
    )


def format_validation_error_fields(errors: list) -> tuple[str, dict[str, str]]:
    """Turn FastAPI/Pydantic validation errors into a primary message + per-field map."""
    fields: dict[str, str] = {}
    primary = "Validation failed"
    skip_loc = {"body", "query", "path", "header"}
    for i, err in enumerate(errors):
        loc_raw = tuple(err.get("loc", ()))
        loc = tuple(str(x) for x in loc_raw)
        error_type = str(err.get("type", ""))
        json_error_pos = next((x for x in loc_raw if isinstance(x, int)), None)

        if error_type == "json_invalid":
            msg = "Malformed JSON body"
            if json_error_pos is not None:
                msg = f"Malformed JSON body at position {json_error_pos}"
            fields["body"] = msg
            if i == 0:
                primary = msg
            continue

        field_key = ".".join(p for p in loc if p not in skip_loc and not p.isdigit()) or "value"
        msg = err.get("msg", "Invalid value")
        if msg.startswith("Value error, "):
            msg = msg[len("Value error, ") :]
        fields[field_key] = msg
        if i == 0:
            if field_key != "value" and field_key not in msg:
                primary = f"{field_key} {msg}"
            else:
                primary = msg
    return primary, fields

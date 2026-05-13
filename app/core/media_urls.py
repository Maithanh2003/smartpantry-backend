"""Build browser-facing URLs for object keys (CDN / R2 public / reverse proxy)."""


def public_object_url(base: str | None, path: str | None) -> str | None:
    if not path or not base:
        return None
    return f"{base.rstrip('/')}/{path.lstrip('/')}"

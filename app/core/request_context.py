from starlette.requests import Request


def client_ip(request: Request) -> str | None:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip() or None
    if request.client:
        return request.client.host
    return None


def client_user_agent(request: Request) -> str | None:
    ua = request.headers.get("user-agent")
    return ua[:2000] if ua else None

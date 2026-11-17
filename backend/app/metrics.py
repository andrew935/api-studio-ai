from fastapi import Request
from prometheus_client import Counter, Histogram


HTTP_REQUESTS_TOTAL = Counter(
    "api_studio_http_requests_total",
    "Total HTTP requests handled by the API.",
    labelnames=("method", "route", "status_class"),
)
HTTP_REQUEST_DURATION_SECONDS = Histogram(
    "api_studio_http_request_duration_seconds",
    "HTTP request duration in seconds.",
    labelnames=("method", "route"),
)


def get_route_template(request: Request) -> str:
    route = request.scope.get("route")
    return getattr(route, "path", "unmatched")


def record_http_request(
    *,
    request: Request,
    status_code: int,
    duration_seconds: float,
) -> None:
    method = request.method
    route = get_route_template(request)
    status_class = f"{status_code // 100}xx"

    HTTP_REQUESTS_TOTAL.labels(
        method=method,
        route=route,
        status_class=status_class,
    ).inc()
    HTTP_REQUEST_DURATION_SECONDS.labels(
        method=method,
        route=route,
    ).observe(duration_seconds)

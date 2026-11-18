# API Studio AI

## Docker

The API, MCP server, and migration job use one immutable application image with
different commands. PostgreSQL uses its own pinned image.

Copy `.env.example` to `.env`, replace `POSTGRES_PASSWORD` and
`JWT_SECRET_KEY`, then build and start the local stack:

```powershell
docker compose up --build --wait
```

The services are bound to localhost:

- FastAPI: `http://127.0.0.1:8000`
- MCP: `http://127.0.0.1:8001/mcp`
- PostgreSQL: `127.0.0.1:5433`

The one-shot `migrate` container must complete successfully before the API and
MCP containers start. Application containers run as a non-root user with a
read-only root filesystem, all Linux capabilities dropped, and only `/tmp` and
the upload volume writable.

If host port `8000` is already used, set both `API_HOST_PORT` and
`PUBLIC_BASE_URL` to another local port, for example `8002`.

### Health checks

- `GET /health/live` reports whether the FastAPI process is running and does
  not access external dependencies. Docker uses this endpoint for its
  container health check.
- `GET /health/ready` runs `SELECT 1` against PostgreSQL. It returns `200` when
  the API can receive traffic and a generic `503` response when the database
  is unavailable, without exposing internal database errors.

### Structured request logs

Application request logs are emitted as one-line JSON to standard error. Each
response includes an `X-Request-ID` header matching the log record. Logged
fields include the HTTP method, path without its query string, status code and
duration. Request bodies, authorization headers, cookies, query parameters and
document contents are not logged. Configure the minimum level with
`LOG_LEVEL`, which defaults to `INFO`.

### Metrics

Prometheus-format metrics are exposed at `GET /metrics/`. The API records a
request counter and request-duration histogram with only low-cardinality
labels: HTTP method, FastAPI route template and status class. Actual resource
IDs, request IDs, user IDs and customer data are never labels. In production,
the metrics endpoint must be reachable only by the monitoring network or
protected by the reverse proxy; it should not be publicly exposed.

Start the optional local Prometheus profile after the application is healthy:

```powershell
docker compose --profile monitoring up -d --wait prometheus
```

The UI is bound to `http://127.0.0.1:9090`. Prometheus scrapes the API every
15 seconds and evaluates alerts for target availability, sustained 5xx rate
and p95 latency. The rules intentionally use `for` durations to avoid alerts
from one isolated failure. This local setup displays firing rules but does not
send notifications; production must route them through Alertmanager or the
chosen cloud monitoring provider.

## Login rate limiting

Login attempts are limited through shared Redis counters for the client IP,
normalized email and IP/email pair. Both IP and email are converted to keyed
HMAC identifiers before being used in Redis keys. Exceeded limits return
`429 Too Many Requests` with `Retry-After`; an unavailable limiter returns a
generic `503` rather than bypassing authentication protection. Redis stores
only temporary counters with TTLs, so persistence is intentionally disabled.

The application reads the direct peer address. A production reverse proxy must
be configured through `FORWARDED_ALLOW_IPS` before forwarded client addresses
are used. Set it to the exact proxy IPs or networks. Uvicorn then accepts
`X-Forwarded-For` only when the direct connection comes from one of those
trusted sources. Never set it to `*` in production, because that lets an
internet client spoof the address used by rate limiting. The Uvicorn `Server`
response header is also disabled.

## Timeout budgets

Production dependency calls use explicit budgets rather than library defaults:

- PostgreSQL waits up to 5 seconds for a pooled connection and limits commands
  to 5 seconds. `pool_pre_ping` avoids handing out stale PostgreSQL connections.
- S3 uses a 3-second connect timeout, 10-second read timeout and two total
  attempts, including the initial request.
- Direct OpenAI calls use a 7-second per-attempt timeout, one retry and a
  15-second outer operation deadline. The outer deadline includes retries and
  backoff, and clients cannot override these values through query parameters.

These values are configuration defaults, not universal constants. They should
be tuned from production latency metrics while preserving an overall request
budget.

Deployment ordering, migration compatibility, readiness gates and rollback
rules are documented in [the deployment runbook](docs/DEPLOYMENT_RUNBOOK.md).

## Bootstrap the first tenant administrator

The bootstrap command creates the first tenant and its admin in one database
transaction. It is a local administrative command, not a public API endpoint.

1. Copy `.env.example` to `.env` and replace every placeholder, especially
   `DATABASE_URL` and `JWT_SECRET_KEY`.
2. Apply the database migrations from the project root:

   ```powershell
   backend/.venv/Scripts/python.exe -m alembic upgrade head
   ```

3. Run the bootstrap command:

   ```powershell
   backend/.venv/Scripts/python.exe -m backend.scripts.bootstrap_admin
   ```

The command prompts for the law firm name, admin email, password, and password
confirmation. The password is hidden while typing and only its Argon2 hash is
stored. If admin creation fails, tenant creation is rolled back.

## Local PostgreSQL

Start the pinned PostgreSQL container and wait for its health check:

```powershell
docker compose up -d --wait postgres
```

The database is exposed on `127.0.0.1:5433` because port `5432` may already
be used by another local PostgreSQL installation. Copy `.env.example` to
`.env` so Docker Compose and the application use the same local password.

Set `DATABASE_URL` in `.env`, then apply migrations:

```powershell
backend/.venv/Scripts/python.exe -m alembic upgrade head
```

Run the explicit PostgreSQL integration test:

```powershell
$env:TEST_POSTGRES_URL = $env:DATABASE_URL
backend/.venv/Scripts/python.exe -m pytest backend/tests/test_postgres_integration.py -q
```

Stop the container without deleting its named data volume:

```powershell
docker compose stop postgres
```

## File storage

Local development defaults to `STORAGE_BACKEND=local` and stores synthetic test
files under `LOCAL_STORAGE_PATH`. Production can use a private S3 bucket:

```env
STORAGE_BACKEND=s3
S3_BUCKET=your-private-document-bucket
S3_REGION=us-east-1
```

`S3_ENDPOINT_URL` is optional for S3-compatible providers. AWS credentials are
not passed in application code; Boto3 uses its standard credential provider
chain, such as a local AWS profile or an IAM role in production.

Stored objects use server-generated keys scoped by tenant and upload request.
The original customer filename is metadata only and never controls the object
key.

## Read-only MCP document search

The project exposes one small Streamable HTTP MCP integration for authenticated,
read-only document retrieval. It reuses the same JWT, active-user database check,
tenant-scoped retrieval service, and approved-document filter as the API.
`user_id` and `tenant_id` are never MCP tool arguments.

Start the API, obtain an access token from `POST /api/v1/auth/login`, and run the
MCP resource server separately:

```powershell
backend/.venv/Scripts/python.exe -m backend.scripts.run_mcp
```

The local endpoint is `http://localhost:8001/mcp`. Configure a compatible MCP
client to send the API access token as a Bearer token. This is a resource-server
integration using the project's existing login flow; a production remote client
that requires OAuth discovery and dynamic authorization needs a dedicated OAuth
authorization-server integration.
